"""Exam-taker pages: choose a quiz, take it against a timer, see the result."""
import json
import re
import sqlite3
import time

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, session, url_for)

from .. import db, metrics
from ..scoring import parse_answers, score_answers

bp = Blueprint("quiz", __name__)

USERNAME_RE = re.compile(r"^[\w .-]{2,32}$")


@bp.get("/")
def index():
    quizzes = db.list_quizzes(db.get_db())
    return render_template("index.html", quizzes=quizzes, username=session.get("username"))


@bp.post("/login")
def login():
    name = (request.form.get("username") or "").strip()
    if not USERNAME_RE.match(name):
        flash("Name must be 2-32 characters: letters, digits, space, dot, dash or underscore.",
              "error")
        return redirect(url_for("quiz.index"))
    session["username"] = name
    return redirect(request.form.get("next") or url_for("quiz.index"))


@bp.post("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("quiz.index"))


@bp.get("/quiz/<int:quiz_id>")
def take(quiz_id):
    if "username" not in session:
        flash("Enter your name before starting a quiz.", "error")
        return redirect(url_for("quiz.index"))
    conn = db.get_db()
    quiz = db.get_quiz(conn, quiz_id) or abort(404)
    questions = db.get_questions(conn, quiz_id)
    if not questions:
        flash("This quiz has no questions yet.", "error")
        return redirect(url_for("quiz.index"))

    # The start time lives in the signed session cookie, so the submit can be
    # handled by a different replica than the one that served this page.
    started = session.setdefault("started", {})
    started[str(quiz_id)] = int(time.time())
    session.modified = True
    metrics.get().attempts_started.labels(quiz_id=str(quiz_id)).inc()

    public_questions = [{k: q[k] for k in ("id", "text", "options")} for q in questions]
    return render_template("quiz.html", quiz=quiz, questions=public_questions)


@bp.post("/quiz/<int:quiz_id>/submit")
def submit(quiz_id):
    username = session.get("username")
    if not username:
        return redirect(url_for("quiz.index"))
    conn = db.get_db()
    quiz = db.get_quiz(conn, quiz_id) or abort(404)
    questions = db.get_questions(conn, quiz_id)

    started_at = session.get("started", {}).pop(str(quiz_id), None)
    session.modified = True
    now = int(time.time())
    duration = now - started_at if started_at else quiz["time_limit_seconds"]
    limit = quiz["time_limit_seconds"] + current_app.config["TIME_GRACE_SECONDS"]

    answers = parse_answers(request.form, questions)
    if duration > limit:
        # Late submission: only the time limit counts, answers are discarded.
        answers = {qid: None for qid in answers}
        flash("Time was up before you submitted, so no answers were counted.", "error")
    score, total, _ = score_answers(questions, answers)

    try:
        attempt_id = db.record_attempt(
            conn, quiz_id, username, score, total, min(duration, limit), answers,
            current_app.config["POD_NAME"],
        )
    except sqlite3.OperationalError:
        metrics.get().db_errors.inc()
        current_app.logger.exception("could not save attempt")
        abort(503)

    m = metrics.get()
    m.submissions.labels(quiz_id=str(quiz_id)).inc()
    m.score_ratio.observe(score / total if total else 0)
    return redirect(url_for("quiz.result", attempt_id=attempt_id))


@bp.get("/result/<int:attempt_id>")
def result(attempt_id):
    conn = db.get_db()
    attempt = db.get_attempt(conn, attempt_id) or abort(404)
    questions = db.get_questions(conn, attempt["quiz_id"])
    saved = {int(k): v for k, v in json.loads(attempt["answers"]).items()}
    _, _, review = score_answers(questions, saved)
    return render_template("result.html", attempt=attempt, review=review)


@bp.get("/leaderboard/<int:quiz_id>")
def leaderboard(quiz_id):
    conn = db.get_db()
    quiz = db.get_quiz(conn, quiz_id) or abort(404)
    return render_template("leaderboard.html", quiz=quiz, rows=db.leaderboard(conn, quiz_id))
