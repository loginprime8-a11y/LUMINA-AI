from __future__ import annotations

import os
from flask import Blueprint, send_from_directory, current_app

ui_bp = Blueprint("ui", __name__)

# Serve a minimal static HTML directly from this file's directory
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
INDEX_PATH = os.path.join(STATIC_DIR, "index.html")

@ui_bp.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

@ui_bp.get("/favicon.ico")
def favicon():
    # not critical; return 204
    from flask import Response
    return Response(status=204)
