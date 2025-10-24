from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health() -> tuple[dict, int]:
    return jsonify({"status": "ok"}), 200
