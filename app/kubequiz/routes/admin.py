"""Admin pages: log in with the admin password and manage quizzes and questions."""
import functools
import hmac
import secrets

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, session, url_for)

from .. import db

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]


@bp.app_context_processor
def inject_csrf():
    return {"csrf_token": _csrf_token}


@bp.before_request
def check_csrf():
    if request.method == "POST":
        expected = session.get("csrf")
        sent = request.form.get("csrf", "")
        if not expected or not hmac.compare_digest(sent, expected):
            abort(400, "invalid CSRF token")


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if hmac.compare_digest(password, current_app.config["ADMIN_PASSWORD"]):
            session["is_admin"] = True
            target = request.form.get("next") or ""
            # Only allow local redirects.
            if not target.startswith("/admin"):
                target = url_for("admin.dashboard")
            return redirect(target)
        flash("Wrong password.", "error")
    return render_template("admin/login.html", next=request.args.get("next", ""))


@bp.post("/logout")
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("quiz.index"))


@bp.get("/")
@admin_required
def dashboard():
    conn = db.get_db()
    return render_template("admin/dashboard.html",
                           quizzes=db.list_quizzes(conn), stats=db.stats(conn))


def _quiz_form():
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    try:
        limit = int(request.form.get("time_limit_seconds") or 0)
    except ValueError:
        limit = 0
    errors = []
    if not 1 <= len(title) <= 120:
        errors.append("Title must be 1-120 characters.")
    if not 30 <= limit <= 7200:
        errors.append("Time limit must be between 30 and 7200 seconds.")
    return title, description, limit, errors


@bp.post("/quizzes")
@admin_required
def create_quiz():
    title, description, limit, errors = _quiz_form()
    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("admin.dashboard"))
    quiz_id = db.create_quiz(db.get_db(), title, description, limit)
    flash("Quiz created. Now add some questions.", "ok")
    return redirect(url_for("admin.edit_quiz", quiz_id=quiz_id))


@bp.get("/quizzes/<int:quiz_id>")
@admin_required
def edit_quiz(quiz_id):
    conn = db.get_db()
    quiz = db.get_quiz(conn, quiz_id) or abort(404)
    return render_template("admin/edit_quiz.html", quiz=quiz,
                           questions=db.get_questions(conn, quiz_id))


@bp.post("/quizzes/<int:quiz_id>")
@admin_required
def update_quiz(quiz_id):
    conn = db.get_db()
    db.get_quiz(conn, quiz_id) or abort(404)
    title, description, limit, errors = _quiz_form()
    if errors:
        for e in errors:
            flash(e, "error")
    else:
        db.update_quiz(conn, quiz_id, title, description, limit)
        flash("Quiz saved.", "ok")
    return redirect(url_for("admin.edit_quiz", quiz_id=quiz_id))


@bp.post("/quizzes/<int:quiz_id>/delete")
@admin_required
def delete_quiz(quiz_id):
    db.delete_quiz(db.get_db(), quiz_id)
    flash("Quiz deleted.", "ok")
    return redirect(url_for("admin.dashboard"))


@bp.post("/quizzes/<int:quiz_id>/questions")
@admin_required
def add_question(quiz_id):
    conn = db.get_db()
    db.get_quiz(conn, quiz_id) or abort(404)
    text = (request.form.get("text") or "").strip()
    options = [o.strip() for o in request.form.getlist("option") if o.strip()]
    try:
        correct = int(request.form.get("correct", -1))
    except ValueError:
        correct = -1
    if not text:
        flash("Question text is required.", "error")
    elif not 2 <= len(options) <= 6:
        flash("Give between 2 and 6 options.", "error")
    elif not 0 <= correct < len(options):
        flash("Pick which option is correct.", "error")
    else:
        db.add_question(conn, quiz_id, text, options, correct)
        flash("Question added.", "ok")
    return redirect(url_for("admin.edit_quiz", quiz_id=quiz_id))


@bp.post("/questions/<int:question_id>/delete")
@admin_required
def delete_question(question_id):
    conn = db.get_db()
    row = conn.execute("SELECT quiz_id FROM questions WHERE id = ?",
                       (question_id,)).fetchone() or abort(404)
    db.delete_question(conn, question_id)
    flash("Question deleted.", "ok")
    return redirect(url_for("admin.edit_quiz", quiz_id=row["quiz_id"]))
