from flask import Blueprint, jsonify
from ..utils.health import run_health_checks

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health() -> tuple[dict, int]:
    checks = run_health_checks()
    return jsonify({"status": checks.get("overall", "ok"), "details": checks}), 200
