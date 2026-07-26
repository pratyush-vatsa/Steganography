"""
Application factory for the Stego web app.

Usage:
    from app import create_app
    app = create_app()
"""
import os
import logging
import tempfile

from flask import Flask, jsonify

from .config import Config

# Register HEIC/HEIF support (the default photo format on iPhones) with
# Pillow. Pillow doesn't support this format natively - pillow-heif adds
# it as a plugin. Registering it once here, at import time, makes
# Image.open() handle .heic/.heif files everywhere in the app without
# needing to touch every call site. Degrades gracefully if the optional
# dependency isn't installed.
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    logging.getLogger(__name__).warning(
        "pillow-heif not installed - .heic/.heif uploads will be rejected. "
        "Install it (see requirements.txt) to support them."
    )


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    Config.validate()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # --- Transient directory for per-request file processing ---
    # STEGO_BASE_DIR (if set, e.g. by render.yaml or a systemd EnvironmentFile)
    # is used as the *parent* of a fresh temp dir so deployments can control
    # where scratch files land (e.g. /tmp on ephemeral hosts).
    base_dir = app.config.get("STEGO_BASE_DIR")
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)
        temp_base_dir = tempfile.mkdtemp(prefix="stego-app-transient-", dir=base_dir)
    else:
        temp_base_dir = tempfile.mkdtemp(prefix="stego-app-transient-")

    app.config["TEMP_BASE_DIR"] = temp_base_dir
    app.logger.info(f"Temporary processing directory created at: {temp_base_dir}")

    # --- Blueprints ---
    from .routes.pages import pages_bp
    from .routes.api import api_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    _register_error_handlers(app)
    return app


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "error": "Not Found"}), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({"success": False, "error": "File is too large (Max 32MB)."}), 413

    @app.errorhandler(500)
    def server_error(error):
        app.logger.error(f"Server error: {error}")
        return jsonify({"success": False, "error": "An internal server error occurred."}), 500
