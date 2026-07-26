"""
Local/dev entrypoint.

Production servers (gunicorn, etc.) should point at `run:app` directly and
never execute this file's __main__ block - see deploy/start.sh.
"""
from dotenv import load_dotenv

load_dotenv()  # reads .env in the project root, if present, before create_app() runs

from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True is a security risk (remote code execution via the
    # Werkzeug debugger) - never enable it outside your own machine.
    app.run(host="127.0.0.1", port=5000, debug=False)
