from __future__ import annotations

import shutil
import subprocess
from typing import Optional

try:
    from PIL import Image, ImageFilter, ImageEnhance
except Exception:  # noqa: BLE001 - optional dependency; handled at runtime
    Image = None  # type: ignore
    ImageFilter = None  # type: ignore
    ImageEnhance = None  # type: ignore


def _which(program: str) -> Optional[str]:
    return shutil.which(program)


def _run_cmd(args: list[str]) -> None:
    subprocess.run(args, check=True)


def _ensure_pil_available() -> None:
    if Image is None:
        raise RuntimeError("Pillow is required for enhancement operations but is not installed")


def _gfpgan_available() -> Optional[str]:
    return _which("gfpgan-ncnn-vulkan")


def enhance_image_general(input_path: str, output_path: str, strength: float = 0.5) -> None:
    """Lightweight general enhancement using PIL: contrast, sharpness, denoise."""
    _ensure_pil_available()
    strength = max(0.0, min(1.0, float(strength)))
    with Image.open(input_path) as img:
        img = img.convert("RGB")
        # Contrast: up to +50%
        contrast_factor = 1.0 + 0.5 * strength
        img = ImageEnhance.Contrast(img).enhance(contrast_factor)
        # Sharpness: up to +200%
        sharp_factor = 1.0 + 2.0 * strength
        img = ImageEnhance.Sharpness(img).enhance(sharp_factor)
        # Mild denoise for high strength
        if strength > 0.6 and ImageFilter is not None:
            img = img.filter(ImageFilter.MedianFilter(size=3))
        img.save(output_path)


def enhance_image_face(input_path: str, output_path: str, strength: float = 0.5) -> None:
    """Face enhancement using GFPGAN if available, otherwise a general enhancement with gentle settings."""
    gfpgan = _gfpgan_available()
    if gfpgan:
        try:
            _run_cmd([gfpgan, "-i", input_path, "-o", output_path])
            return
        except Exception:
            pass
    # Fallback: slightly stronger sharpen + small contrast boost
    _ensure_pil_available()
    strength = max(0.0, min(1.0, float(strength)))
    with Image.open(input_path) as img:
        img = img.convert("RGB")
        contrast_factor = 1.0 + 0.3 * strength
        img = ImageEnhance.Contrast(img).enhance(contrast_factor)
        sharp_factor = 1.0 + 3.0 * strength
        img = ImageEnhance.Sharpness(img).enhance(sharp_factor)
        if ImageFilter is not None:
            img = img.filter(ImageFilter.SMOOTH)
        img.save(output_path)


def repair_image(input_path: str, output_path: str, strength: float = 0.5) -> None:
    """Simple artifact repair/denoise. Tries to preserve details while removing noise."""
    _ensure_pil_available()
    strength = max(0.0, min(1.0, float(strength)))
    with Image.open(input_path) as img:
        img = img.convert("RGB")
        if ImageFilter is not None:
            if strength >= 0.75:
                img = img.filter(ImageFilter.MedianFilter(size=5))
                img = img.filter(ImageFilter.SMOOTH_MORE)
            elif strength >= 0.4:
                img = img.filter(ImageFilter.MedianFilter(size=3))
                img = img.filter(ImageFilter.SMOOTH)
            else:
                img = img.filter(ImageFilter.SMOOTH)
        img = ImageEnhance.Sharpness(img).enhance(1.0 + 0.5 * strength)
        img.save(output_path)


def apply_enhancements(input_path: str, output_path: str, mode: str, strength: float = 0.5) -> None:
    mode_l = (mode or "").strip().lower()
    if mode_l in {"face", "face_enhance", "face-enhance"}:
        enhance_image_face(input_path, output_path, strength=strength)
    elif mode_l in {"repair", "ai_repair", "ai-repair"}:
        repair_image(input_path, output_path, strength=strength)
    else:
        enhance_image_general(input_path, output_path, strength=strength)
