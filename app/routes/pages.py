"""
Static/info page routes: the main app UI plus the documentation-style pages
(explanation, demos, flowchart, resources, quiz, glossary, security guide).
"""
import os

from flask import Blueprint, render_template, send_from_directory, current_app

pages_bp = Blueprint("pages", __name__)


def _pages_dir():
    return os.path.join(current_app.static_folder, "pages")


@pages_bp.route("/")
def index():
    return render_template("index.html")


@pages_bp.route("/explanation")
def explanation():
    return send_from_directory(_pages_dir(), "explanation.html")


@pages_bp.route("/demos")
def demos():
    return send_from_directory(_pages_dir(), "demos.html")


@pages_bp.route("/flowchart")
def flowchart():
    return send_from_directory(_pages_dir(), "flowchart.html")


@pages_bp.route("/resources")
def resources():
    return send_from_directory(_pages_dir(), "resources.html")


@pages_bp.route("/quiz")
def quiz():
    return send_from_directory(_pages_dir(), "quiz.html")


@pages_bp.route("/glossary")
def glossary():
    return send_from_directory(_pages_dir(), "glossary.html")


@pages_bp.route("/security-guide")
def security_guide():
    return send_from_directory(_pages_dir(), "security_guide.html")
