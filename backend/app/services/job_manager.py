from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Dict, Optional, Literal
from concurrent.futures import ThreadPoolExecutor

from .pipeline import process_media


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


JobType = Literal["image", "video"]


@dataclass
class Job:
    id: str
    input_path: str
    media_type: JobType
    options: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    output_path: Optional[str] = None
    progress: float = 0.0
    error: Optional[str] = None
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    def output_filename(self) -> str:
        if self.output_path:
            return os.path.basename(self.output_path)
        return f"{self.id}_output"


class JobManager:
    _shared: Optional["JobManager"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._jobs_lock: Lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="job-worker")
        self._logger = logging.getLogger(__name__)

    @classmethod
    def get_shared(cls) -> "JobManager":
        with cls._lock:
            if cls._shared is None:
                cls._shared = JobManager()
            return cls._shared

    def create_job(self, job_id: str, input_path: str, media_type: JobType, options: Dict[str, Any]) -> Job:
        job = Job(id=job_id, input_path=input_path, media_type=media_type, options=options)
        with self._jobs_lock:
            self._jobs[job_id] = job
        return job

    def enqueue(self, job: Job) -> None:
        self._executor.submit(self._run_job, job)

    def _run_job(self, job: Job) -> None:
        job.status = JobStatus.RUNNING
        self._update_job(job)
        try:
            output_path = process_media(job, self)
            job.output_path = output_path
            job.progress = 1.0
            job.status = JobStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001 - surface exceptions to job record
            self._logger.exception("Job failed: %s", job.id)
            job.error = str(exc)
            job.status = JobStatus.FAILED
        finally:
            self._update_job(job)

    def _update_job(self, job: Job) -> None:
        job.updated_at = time.time()
        with self._jobs_lock:
            self._jobs[job.id] = job

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._jobs_lock:
            return self._jobs.get(job_id)

    def set_progress(self, job: Job, progress: float) -> None:
        job.progress = max(0.0, min(1.0, progress))
        self._update_job(job)

    def serialize_job(self, job: Job) -> Dict[str, Any]:
        status_value = job.status.value if isinstance(job.status, JobStatus) else str(job.status)
        return {
            "id": job.id,
            "status": status_value,
            "progress": job.progress,
            "error": job.error,
            "media_type": job.media_type,
            "input_path": job.input_path,
            "output_path": job.output_path,
            "download_url": f"/api/download/{job.id}" if status_value == "COMPLETED" and job.output_path else None,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "options": job.options,
        }
