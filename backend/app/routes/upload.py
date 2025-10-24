import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from ..utils.files import allowed_file, detect_media_type
from ..services.job_manager import JobManager

upload_bp = Blueprint("upload", __name__)
job_manager = JobManager.get_shared()


@upload_bp.post("/upload")
def upload():
    if "file" not in request.files:
        return jsonify({"error": "missing_file"}), 400

    uploaded_file = request.files["file"]

    if uploaded_file.filename == "":
        return jsonify({"error": "empty_filename"}), 400

    filename = secure_filename(uploaded_file.filename)

    if not allowed_file(filename):
        return jsonify({"error": "unsupported_file_type"}), 400

    job_id = str(uuid.uuid4())
    input_dir = current_app.config["STORAGE_INPUT_DIR"]
    os.makedirs(input_dir, exist_ok=True)
    input_path = os.path.join(input_dir, f"{job_id}_{filename}")
    uploaded_file.save(input_path)

    media_type = detect_media_type(filename)

    # Optional processing options (parse safely)
    form = request.form

    def _parse_float(name: str):
        val = form.get(name)
        if val is None or val == "":
            return None
        try:
            return float(val)
        except Exception:
            return None

    def _parse_int(name: str):
        val = form.get(name)
        if val is None or val == "":
            return None
        try:
            return int(val)
        except Exception:
            return None

    scale = _parse_float("scale")
    target_width = _parse_int("target_width")
    target_height = _parse_int("target_height")
    video_bitrate = form.get("video_bitrate") or None
    output_format = form.get("format") or None

    options = {
        "scale": scale,
        "target_width": target_width,
        "target_height": target_height,
        "video_bitrate": video_bitrate,
        "format": output_format,
    }

    job = job_manager.create_job(job_id=job_id, input_path=input_path, media_type=media_type, options=options)
    job_manager.enqueue(job)

    return jsonify({"job_id": job_id}), 202
