import os
from pathlib import Path
from typing import Final


class AppConfig:
    DEFAULT_STORAGE_ROOT: Final[Path] = Path(os.environ.get("STORAGE_ROOT", "/workspace/backend/storage"))
    DEFAULT_TMP_ROOT: Final[Path] = Path(os.environ.get("TMP_ROOT", "/workspace/backend/tmp"))
    DEFAULT_MAX_UPLOAD_MB: Final[int] = int(os.environ.get("MAX_UPLOAD_MB", "1024"))  # 1 GB

    @classmethod
    def storage_input_dir(cls) -> str:
        return str(cls.DEFAULT_STORAGE_ROOT / "input")

    @classmethod
    def storage_output_dir(cls) -> str:
        return str(cls.DEFAULT_STORAGE_ROOT / "output")

    @classmethod
    def tmp_frames_dir(cls) -> str:
        return str(cls.DEFAULT_TMP_ROOT / "frames")

    @classmethod
    def max_upload_bytes(cls) -> int:
        return cls.DEFAULT_MAX_UPLOAD_MB * 1024 * 1024


def ensure_directories_exist() -> None:
    Path(AppConfig.storage_input_dir()).mkdir(parents=True, exist_ok=True)
    Path(AppConfig.storage_output_dir()).mkdir(parents=True, exist_ok=True)
    Path(AppConfig.tmp_frames_dir()).mkdir(parents=True, exist_ok=True)
