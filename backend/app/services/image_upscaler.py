from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional
import os

try:
    from PIL import Image
except Exception:  # noqa: BLE001 - optional dependency; handled at runtime
    Image = None  # type: ignore


def _which(program: str) -> Optional[str]:
    return shutil.which(program)


def _upscale_with_realesrgan_cli(input_path: str, output_path: str, scale: float) -> bool:
    exe = _which("realesrgan-ncnn-vulkan")
    if exe is None:
        return False
    cmd = [exe, "-i", input_path, "-o", output_path, "-s", str(int(scale))]
    # Provide models directory if present and set threads/gpu flags
    models_dir = os.environ.get("REALESRGAN_MODELS_DIR", "/app/models/realesrgan")
    if os.path.isdir(models_dir):
        cmd.extend(["-m", models_dir])
    # Allow users to set NCNN threading; defaults are usually optimal
    if os.environ.get("NCNN_THREADS"):
        cmd.extend(["-t", os.environ["NCNN_THREADS"]])
    if os.environ.get("NCNN_GPU") in {"0", "1"}:
        cmd.extend(["-g", os.environ["NCNN_GPU"]])
    subprocess.run(cmd, check=True)
    return True


def _upscale_with_pillow(input_path: str, output_path: str, scale: Optional[float], target_width: Optional[int], target_height: Optional[int]) -> None:
    if Image is None:
        # Fallback: no PIL, copy the file unchanged
        shutil.copy2(input_path, output_path)
        return

    with Image.open(input_path) as img:
        if target_width and target_height:
            new_size = (target_width, target_height)
        elif scale and scale > 0:
            new_size = (int(img.width * scale), int(img.height * scale))
        else:
            new_size = (img.width, img.height)

        resample = Image.Resampling.BICUBIC if hasattr(Image, "Resampling") else Image.BICUBIC
        upscaled = img.resize(new_size, resample=resample)

        # Ensure correct format by extension
        ext = os.path.splitext(output_path)[1].lower()
        if ext in {".jpg", ".jpeg"}:
            upscaled.save(output_path, format="JPEG", quality=95)
        elif ext == ".webp":
            upscaled.save(output_path, format="WEBP", quality=95)
        else:
            upscaled.save(output_path)


def upscale_image(
    input_path: str,
    output_path: str,
    scale: Optional[float] = None,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
) -> None:
    """Upscale an image using Real-ESRGAN CLI if available, otherwise Pillow.

    If both target_width and target_height are provided they are used; otherwise, scale is used.
    """
    # Prefer CLI if a valid integer scale factor and CLI is available
    if scale and float(scale).is_integer() and int(scale) in {2, 3, 4}:
        try:
            used_cli = _upscale_with_realesrgan_cli(input_path, output_path, scale=scale)
            if used_cli:
                return
        except Exception:
            # Fall back to Pillow path on any error
            pass

    _upscale_with_pillow(
        input_path=input_path,
        output_path=output_path,
        scale=scale,
        target_width=target_width,
        target_height=target_height,
    )
