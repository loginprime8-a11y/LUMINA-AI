import os
from flask import Blueprint, jsonify, send_file, abort, current_app

from ..services.job_manager import JobManager

jobs_bp = Blueprint("jobs", __name__)
job_manager = JobManager.get_shared()


@jobs_bp.get("/jobs")
def list_jobs():
    jobs = job_manager.list_jobs()
    return jsonify([job_manager.serialize_job(j) for j in jobs]), 200

@jobs_bp.get("/job/<job_id>")
def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if job is None:
        return jsonify({"error": "job_not_found"}), 404
    return jsonify(job_manager.serialize_job(job)), 200


@jobs_bp.get("/download/<job_id>")
def download(job_id: str):
    job = job_manager.get_job(job_id)
    # Robust completion check regardless of Enum/string representation
    status_value = None
    if job is not None:
        try:
            status_value = job.status.value  # type: ignore[attr-defined]
        except Exception:
            status_value = str(job.status) if job and job.status is not None else None
    if (
        job is None
        or job.output_path is None
        or status_value != "COMPLETED"
        or not os.path.exists(job.output_path)
    ):
        abort(404)
    return send_file(job.output_path, as_attachment=True, download_name=os.path.basename(job.output_path))


@jobs_bp.get("/download/<job_id>/hq")
def download_hq(job_id: str):
    # Re-encode images/videos to high-quality settings for download
    job = job_manager.get_job(job_id)
    status_value = None
    if job is not None:
        try:
            status_value = job.status.value
        except Exception:
            status_value = str(job.status) if job and job.status is not None else None
    if job is None or job.output_path is None or status_value != "COMPLETED" or not os.path.exists(job.output_path):
        abort(404)

    out_path = job.output_path
    base, ext = os.path.splitext(out_path.lower())

    # If image: ensure high quality export via Pillow
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            from PIL import Image
            with Image.open(job.output_path) as img:
                tmp = os.path.join(current_app.config["STORAGE_OUTPUT_DIR"], f"{job.id}_hq{ext}")
                if ext in {".jpg", ".jpeg"}:
                    img.save(tmp, format="JPEG", quality=98)
                elif ext == ".webp":
                    img.save(tmp, format="WEBP", quality=98, method=6)
                else:
                    img.save(tmp)
                out_path = tmp
        except Exception:
            pass
    else:
        # If video: re-mux with a high bitrate setting using ffmpeg if available
        from ..utils.ffmpeg import ffmpeg_available, _run_command  # type: ignore
        if ffmpeg_available():
            tmp = os.path.join(current_app.config["STORAGE_OUTPUT_DIR"], f"{job.id}_hq.mp4")
            try:
                _run_command([
                    "ffmpeg", "-y", "-i", job.output_path,
                    "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                    "-c:a", "aac", "-b:a", "256k",
                    tmp,
                ])
                out_path = tmp
            except Exception:
                pass

    return send_file(out_path, as_attachment=True, download_name=os.path.basename(out_path))


@jobs_bp.post("/job/<job_id>/cancel")
def cancel_job(job_id: str):
    accepted = job_manager.cancel_job(job_id)
    if not accepted:
        return jsonify({"error": "cannot_cancel"}), 400
    job = job_manager.get_job(job_id)
    return jsonify(job_manager.serialize_job(job) if job else {"id": job_id, "status": "UNKNOWN"}), 200
