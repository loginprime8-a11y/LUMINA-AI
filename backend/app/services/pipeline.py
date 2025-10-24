from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Optional, Dict, Any

from ..utils.config import AppConfig
from ..utils import ffmpeg as ffm
from .image_upscaler import upscale_image
from .enhancers import apply_enhancements


@dataclass
class ProcessOptions:
    scale: Optional[float] = None
    target_width: Optional[int] = None
    target_height: Optional[int] = None
    video_bitrate: Optional[str] = None
    format: Optional[str] = None
    mode: Optional[str] = None
    strength: Optional[float] = None
    interpolate: Optional[bool] = None
    interp_factor: Optional[int] = None
    realesrgan_model: Optional[str] = None
    rife_factor: Optional[int] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ProcessOptions":
        return ProcessOptions(
            scale=data.get("scale"),
            target_width=data.get("target_width"),
            target_height=data.get("target_height"),
            video_bitrate=data.get("video_bitrate"),
            format=data.get("format"),
            mode=data.get("mode"),
            strength=data.get("strength"),
            interpolate=data.get("interpolate"),
            interp_factor=data.get("interp_factor"),
            realesrgan_model=data.get("realesrgan_model"),
            rife_factor=data.get("rife_factor"),
        )


def process_media(job: Job, job_manager) -> str:
    options = ProcessOptions.from_dict(job.options or {})

    if job.media_type == "image":
        return _process_image(job, options, job_manager)

    if job.media_type == "video":
        return _process_video(job, options, job_manager)

    raise ValueError(f"Unsupported media type: {job.media_type}")


def _process_image(job: Job, options: ProcessOptions, job_manager) -> str:
    output_dir = AppConfig.storage_output_dir()
    os.makedirs(output_dir, exist_ok=True)

    base_name, _ = os.path.splitext(os.path.basename(job.input_path))
    output_format = (options.format or "png").lower()
    if output_format not in {"png", "jpg", "jpeg", "webp"}:
        output_format = "png"

    suffix = "upscaled"
    if options.mode:
        suffix = options.mode.replace(" ", "_")
    output_path = os.path.join(output_dir, f"{base_name}_{suffix}.{output_format}")

    # Early cancel check
    if getattr(job, "cancel_requested", False):
        raise RuntimeError("cancelled")

    # First, upscale if requested
    if options.scale or options.target_width or options.target_height:
        temp_up = os.path.join(output_dir, f"{base_name}_tmp_upscale.{output_format}")
        upscale_image(
            input_path=job.input_path,
            output_path=temp_up,
            scale=options.scale,
            target_width=options.target_width,
            target_height=options.target_height,
            realesrgan_model=options.realesrgan_model,
        )
        src_for_enhance = temp_up
    else:
        src_for_enhance = job.input_path

    # Then, apply enhancements (general/face/repair) if requested or default to general
    apply_enhancements(
        input_path=src_for_enhance,
        output_path=output_path,
        mode=options.mode or "general",
        strength=float(options.strength) if options.strength is not None else 0.6,
    )

    job_manager.set_progress(job, 1.0)
    return output_path


def _process_video(job: Job, options: ProcessOptions, job_manager) -> str:
    if not ffm.ffmpeg_available():
        raise RuntimeError("ffmpeg is required for video processing but was not found in PATH")

    frames_root = AppConfig.tmp_frames_dir()
    frames_job_dir = os.path.join(frames_root, job.id)
    os.makedirs(frames_job_dir, exist_ok=True)

    # Stage 1: Extract frames and audio
    if getattr(job, "cancel_requested", False):
        raise RuntimeError("cancelled")

    fps = ffm.get_video_fps(job.input_path) or 30.0
    total_frames = ffm.extract_frames(job.input_path, frames_job_dir)
    audio_path = os.path.join(frames_job_dir, "audio.aac")
    audio_extracted = ffm.extract_audio(job.input_path, audio_path)
    job_manager.set_progress(job, 0.1)

    # Stage 2: Upscale + Enhance frames (and optionally interpolate later)
    frame_files = ffm.list_frame_files(frames_job_dir)
    if total_frames and len(frame_files) != total_frames:
        total_frames = len(frame_files)

    processed_dir = os.path.join(frames_job_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    completed = 0
    for frame_path in frame_files:
        if getattr(job, "cancel_requested", False):
            raise RuntimeError("cancelled")
        base = os.path.basename(frame_path)
        out_frame = os.path.join(processed_dir, base)
        # Upscale first into a temp, then enhance into final processed frame
        temp_up = os.path.join(processed_dir, f"tmp_{base}")
        upscale_image(
            input_path=frame_path,
            output_path=temp_up,
            scale=options.scale,
            target_width=options.target_width,
            target_height=options.target_height,
            realesrgan_model=options.realesrgan_model,
        )
        apply_enhancements(
            input_path=temp_up,
            output_path=out_frame,
            mode=options.mode or "general",
            strength=float(options.strength) if options.strength is not None else 0.6,
        )
        completed += 1
        # Scale progress for this stage between 0.1 and 0.9
        if total_frames:
            stage_progress = 0.1 + 0.8 * (completed / total_frames)
            job_manager.set_progress(job, stage_progress)

    # Stage 3: Assemble video
    output_dir = AppConfig.storage_output_dir()
    os.makedirs(output_dir, exist_ok=True)
    base_name, _ = os.path.splitext(os.path.basename(job.input_path))
    output_format = (options.format or "mp4").lower()
    if output_format not in {"mp4", "mov", "mkv", "webm"}:
        output_format = "mp4"
    suffix = "enhanced"
    if options.mode:
        suffix = options.mode.replace(" ", "_")
    output_path = os.path.join(output_dir, f"{base_name}_{suffix}.{output_format}")

    if getattr(job, "cancel_requested", False):
        raise RuntimeError("cancelled")

    # Optional interpolation: if requested, increase fps
    interp_fps = None
    # Prefer explicit rife_factor if provided, else use generic interp_factor
    chosen_factor = options.rife_factor if (options.rife_factor and options.rife_factor > 1) else options.interp_factor
    if options.interpolate and chosen_factor and chosen_factor > 1:
        try:
            interp_fps = float(fps) * float(chosen_factor)
        except Exception:
            interp_fps = None

    ffm.assemble_video(
        frames_dir=processed_dir,
        fps=fps,
        output_path=output_path,
        audio_path=audio_path if audio_extracted else None,
        video_bitrate=options.video_bitrate,
        interpolate_to_fps=interp_fps,
    )

    job_manager.set_progress(job, 0.98)

    # Cleanup original frames to reduce disk usage (keep processed frames for debugging)
    try:
        shutil.rmtree(os.path.join(frames_job_dir, "raw"), ignore_errors=True)
    except Exception:
        pass

    job_manager.set_progress(job, 1.0)
    return output_path
