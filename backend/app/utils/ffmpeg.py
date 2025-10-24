from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import List, Optional


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _run_command(args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)


def get_video_fps(input_video_path: str) -> Optional[float]:
    try:
        proc = _run_command([
            "ffprobe",
            "-v",
            "0",
            "-select_streams",
            "v:0",
            "-of",
            "csv=p=0",
            "-show_entries",
            "stream=r_frame_rate",
            input_video_path,
        ])
        rate = proc.stdout.strip()
        if "/" in rate:
            num, den = rate.split("/", 1)
            num_f = float(num)
            den_f = float(den)
            if den_f == 0:
                return None
            return num_f / den_f
        return float(rate)
    except Exception:
        return None


def extract_frames(input_video_path: str, frames_dir: str) -> Optional[int]:
    os.makedirs(frames_dir, exist_ok=True)
    raw_dir = os.path.join(frames_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    pattern = os.path.join(raw_dir, "%08d.png")
    _run_command(["ffmpeg", "-y", "-i", input_video_path, "-vsync", "0", pattern])

    # Count frames
    count = 0
    for name in os.listdir(raw_dir):
        if re.match(r"^\d{8}\.png$", name):
            count += 1
    return count


def list_frame_files(frames_dir: str) -> list[str]:
    raw_dir = os.path.join(frames_dir, "raw")
    files = [os.path.join(raw_dir, f) for f in os.listdir(raw_dir) if re.match(r"^\d{8}\.png$", f)]
    files.sort()
    return files


def extract_audio(input_video_path: str, audio_output_path: str) -> bool:
    try:
        _run_command(["ffmpeg", "-y", "-i", input_video_path, "-vn", "-acodec", "aac", audio_output_path])
        return True
    except Exception:
        return False


def assemble_video(
    frames_dir: str,
    fps: float,
    output_path: str,
    audio_path: Optional[str] = None,
    video_bitrate: Optional[str] = None,
    interpolate_to_fps: Optional[float] = None,
) -> None:
    processed_dir = frames_dir
    pattern = os.path.join(processed_dir, "%08d.png")

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        pattern,
    ]

    # Optional frame interpolation to a higher fps using FFmpeg minterpolate
    if interpolate_to_fps and interpolate_to_fps > fps:
        cmd.extend(["-vf", f"minterpolate=fps={interpolate_to_fps}"])

    cmd.extend([
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "18",
    ])

    if video_bitrate:
        cmd.extend(["-b:v", video_bitrate])

    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path, "-c:a", "aac", "-b:a", "192k"])  # add audio

    cmd.append(output_path)

    _run_command(cmd)
