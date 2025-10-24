from __future__ import annotations

import os
import shutil
from typing import Dict, Any, Optional


def _which(name: str) -> Optional[str]:
    return shutil.which(name)


def _dir_exists(path: Optional[str]) -> bool:
    return bool(path and os.path.isdir(path))


def run_health_checks() -> Dict[str, Any]:
    """Collects availability for CLIs and core tools.

    Does not run heavy computations; only checks binary presence and model directories.
    """
    status: Dict[str, Any] = {}

    # Core tools
    status["ffmpeg"] = _which("ffmpeg") is not None and _which("ffprobe") is not None

    # AI CLIs
    clis: Dict[str, Any] = {}
    clis["rife"] = {
        "available": _which("rife-ncnn-vulkan") is not None,
        "models": _dir_exists(os.environ.get("RIFE_MODELS_DIR", "/app/models/rife")),
        "path": _which("rife-ncnn-vulkan"),
    }
    clis["codeformer"] = {
        "available": _which("codeformer-ncnn-vulkan") is not None,
        "models": _dir_exists(os.environ.get("CODEFORMER_MODELS_DIR", "/app/models/codeformer")),
        "path": _which("codeformer-ncnn-vulkan"),
    }
    clis["gfpgan"] = {
        "available": _which("gfpgan-ncnn-vulkan") is not None,
        "models": _dir_exists(os.environ.get("GFPGAN_MODELS_DIR", "/app/models/gfpgan")),
        "path": _which("gfpgan-ncnn-vulkan"),
    }
    clis["realesrgan"] = {
        "available": _which("realesrgan-ncnn-vulkan") is not None,
        "models": _dir_exists(os.environ.get("REALESRGAN_MODELS_DIR", "/app/models/realesrgan")),
        "path": _which("realesrgan-ncnn-vulkan"),
    }

    status["clis"] = clis

    # Overall
    all_good = status["ffmpeg"] and any(v.get("available") for v in clis.values())
    status["overall"] = "ok" if all_good else "degraded"
    return status
