from __future__ import annotations

import io
import os
import uuid
from flask import Blueprint, request, send_file, jsonify, current_app
from werkzeug.utils import secure_filename

from ..services.enhancers import apply_enhancements
from ..services.image_upscaler import upscale_image
from ..utils.files import allowed_file, detect_media_type

preview_bp = Blueprint("preview", __name__)

@preview_bp.post("/preview")
def preview():
    if "file" not in request.files:
        return jsonify({"error": "missing_file"}), 400

    uploaded_file = request.files["file"]
    if uploaded_file.filename == "":
        return jsonify({"error": "empty_filename"}), 400

    filename = secure_filename(uploaded_file.filename)
    if not allowed_file(filename):
        return jsonify({"error": "unsupported_file_type"}), 400

    # Images only for preview
    if detect_media_type(filename) != "image":
        return jsonify({"error": "preview_images_only"}), 400

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
    mode = form.get("mode") or "general"
    strength = _parse_float("strength") or 0.6

    # Save input to a temp path
    job_id = str(uuid.uuid4())
    input_dir = current_app.config["STORAGE_INPUT_DIR"]
    os.makedirs(input_dir, exist_ok=True)
    input_path = os.path.join(input_dir, f"{job_id}_{filename}")
    uploaded_file.save(input_path)

    # Create two outputs: original resized/upscaled (left) and enhanced (right)
    out_dir = current_app.config["STORAGE_OUTPUT_DIR"]
    os.makedirs(out_dir, exist_ok=True)
    left_path = os.path.join(out_dir, f"{job_id}_left.png")
    right_path = os.path.join(out_dir, f"{job_id}_right.png")

    # If scale provided, upscale to left; else copy as-is
    if scale or target_width or target_height:
        upscale_image(input_path, left_path, scale=scale, target_width=target_width, target_height=target_height)
        src_for_enhance = left_path
    else:
        import shutil
        shutil.copy2(input_path, left_path)
        src_for_enhance = input_path

    apply_enhancements(src_for_enhance, right_path, mode=mode, strength=strength)

    # Return a simple multipart-like zip would be ideal; but to keep it simple, return right image only
    # For side-by-side in UI, we will fetch both URLs separately
    return jsonify({
        "left_url": f"/api/download_preview/{os.path.basename(left_path)}",
        "right_url": f"/api/download_preview/{os.path.basename(right_path)}",
    })

@preview_bp.get("/download_preview/<name>")
def download_preview(name: str):
    out_dir = current_app.config["STORAGE_OUTPUT_DIR"]
    path = os.path.join(out_dir, name)
    if not os.path.exists(path):
        return jsonify({"error": "not_found"}), 404
    return send_file(path, as_attachment=False)
