import os
from flask import Blueprint, jsonify, send_file, abort

from ..services.job_manager import JobManager

jobs_bp = Blueprint("jobs", __name__)
job_manager = JobManager.get_shared()


@jobs_bp.get("/job/<job_id>")
def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if job is None:
        return jsonify({"error": "job_not_found"}), 404
    return jsonify(job_manager.serialize_job(job)), 200


@jobs_bp.get("/download/<job_id>")
def download(job_id: str):
    job = job_manager.get_job(job_id)
    if job is None or job.output_path is None or (str(job.status) != "JobStatus.COMPLETED" and str(job.status) != "COMPLETED"):
        abort(404)
    return send_file(job.output_path, as_attachment=True, download_name=os.path.basename(job.output_path))
