import os
from typing import Literal


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def allowed_file(filename: str) -> bool:
    ext = get_file_extension(filename)
    return ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS


def detect_media_type(filename: str) -> Literal["image", "video"]:
    ext = get_file_extension(filename)
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    raise ValueError(f"Unsupported file extension: {ext}")
