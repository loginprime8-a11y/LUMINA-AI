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
    CANCELLED = "CANCELLED"


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
    cancel_requested: bool = False

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
        # Make worker concurrency configurable via env var JOB_WORKERS (default 2)
        try:
            import os
            workers = int(os.environ.get("JOB_WORKERS", "2"))
            if workers < 1:
                workers = 1
        except Exception:
            workers = 2
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="job-worker")
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

    def list_jobs(self) -> list[Job]:
        with self._jobs_lock:
            return list(self._jobs.values())

    def cancel_job(self, job_id: str) -> bool:
        """Request cancellation for a job.

        Returns True if the cancellation was accepted, False if not found or not cancellable.
        """
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                return False
            job.cancel_requested = True
            # If the job hasn't started yet, mark as cancelled immediately
            if job.status == JobStatus.PENDING:
                job.status = JobStatus.CANCELLED
            self._jobs[job_id] = job
            return True

    def enqueue(self, job: Job) -> None:
        self._executor.submit(self._run_job, job)

    def _run_job(self, job: Job) -> None:
        # Skip running if cancellation was requested before start
        if job.cancel_requested and job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            self._update_job(job)
            return
        job.status = JobStatus.RUNNING
        self._update_job(job)
        try:
            output_path = process_media(job, self)
            job.output_path = output_path
            job.progress = 1.0
            # If cancellation was requested during processing, honor it
            if job.cancel_requested:
                job.status = JobStatus.CANCELLED
            else:
                job.status = JobStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001 - surface exceptions to job record
            self._logger.exception("Job failed: %s", job.id)
            job.error = str(exc)
            # Differentiate between failure and cancellation if requested
            job.status = JobStatus.CANCELLED if job.cancel_requested else JobStatus.FAILED
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
