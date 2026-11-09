"""Small JSON API, handy for curl-based demos of load balancing."""
from flask import Blueprint, current_app, jsonify

from .. import db

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/info")
def info():
    """Which pod answered? `for i in $(seq 10); do curl -s .../api/info; done`"""
    return jsonify(pod=current_app.config["POD_NAME"], version=current_app.config["APP_VERSION"])


@bp.get("/quizzes")
def quizzes():
    rows = db.list_quizzes(db.get_db())
    return jsonify([dict(r) for r in rows])


@bp.get("/stats")
def stats():
    data = db.stats(db.get_db())
    data["pod"] = current_app.config["POD_NAME"]
    return jsonify(data)
