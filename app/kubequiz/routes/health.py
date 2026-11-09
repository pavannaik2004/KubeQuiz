"""Kubernetes probes.

/healthz  liveness:  the process is up and answering HTTP.
/readyz   readiness: the shared database is reachable, so it is safe to
          send traffic here. A pod that fails this is taken out of the
          Service's endpoints but is not restarted.
"""
import sqlite3

from flask import Blueprint, current_app, jsonify

from .. import db

bp = Blueprint("health", __name__)


@bp.get("/healthz")
def healthz():
    return jsonify(status="ok", pod=current_app.config["POD_NAME"])


@bp.get("/readyz")
def readyz():
    try:
        db.get_db().execute("SELECT 1 FROM quizzes LIMIT 1").fetchall()
    except sqlite3.Error as exc:
        current_app.logger.error("readiness check failed: %s", exc)
        return jsonify(status="unavailable", error=str(exc)), 503
    return jsonify(status="ready", pod=current_app.config["POD_NAME"])
