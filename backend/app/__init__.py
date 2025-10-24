import logging
from flask import Flask
from flask_cors import CORS

from .utils.config import AppConfig, ensure_directories_exist
from .routes.health import health_bp
from .routes.upload import upload_bp
from .routes.jobs import jobs_bp


def create_app() -> Flask:
    """Create and configure the Flask application."""
    logging.basicConfig(level=logging.INFO)

    ensure_directories_exist()

    app = Flask(__name__)
    app.config.from_mapping(
        STORAGE_INPUT_DIR=AppConfig.storage_input_dir(),
        STORAGE_OUTPUT_DIR=AppConfig.storage_output_dir(),
        TMP_FRAMES_DIR=AppConfig.tmp_frames_dir(),
        MAX_CONTENT_LENGTH=AppConfig.max_upload_bytes(),
    )

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(upload_bp, url_prefix="/api")
    app.register_blueprint(jobs_bp, url_prefix="/api")

    return app
