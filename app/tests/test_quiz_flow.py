import time

from kubequiz import db


def _questions(app, quiz_id=1):
    with app.app_context():
        return db.get_questions(db.get_db(), quiz_id)


def test_home_lists_seeded_quizzes(client):
    html = client.get("/").get_data(as_text=True)
    assert "Kubernetes Basics" in html
    assert "Docker Fundamentals" in html
    assert "test-pod" in html  # pod name in footer


def test_bad_username_rejected(client):
    client.post("/login", data={"username": "x"})
    with client.session_transaction() as s:
        assert "username" not in s


def test_quiz_requires_name(client):
    resp = client.get("/quiz/1")
    assert resp.status_code == 302


def test_quiz_page_hides_answers(app, student):
    html = student.get("/quiz/1").get_data(as_text=True)
    assert "correct_index" not in html
    assert 'name="q' in html


def test_full_attempt_perfect_score(app, student):
    student.get("/quiz/1")
    qs = _questions(app)
    form = {f"q{q['id']}": str(q["correct_index"]) for q in qs}
    resp = student.post("/quiz/1/submit", data=form)
    assert resp.status_code == 302
    html = student.get(resp.headers["Location"]).get_data(as_text=True)
    assert f"{len(qs)} / {len(qs)}" in html

    board = student.get("/leaderboard/1").get_data(as_text=True)
    assert "Asha" in board


def test_late_submission_scores_zero(app, student):
    student.get("/quiz/1")
    with student.session_transaction() as s:
        s["started"] = {"1": int(time.time()) - 10_000}
    qs = _questions(app)
    form = {f"q{q['id']}": str(q["correct_index"]) for q in qs}
    resp = student.post("/quiz/1/submit", data=form)
    html = student.get(resp.headers["Location"]).get_data(as_text=True)
    assert f"0 / {len(qs)}" in html


def test_submit_works_without_session_cookie_from_same_pod(app, student):
    """Stateless: a second app instance (another 'pod') with the same SECRET_KEY
    accepts the session cookie issued by the first."""
    from kubequiz import create_app
    student.get("/quiz/1")
    other = create_app({**{k: app.config[k] for k in ("SECRET_KEY", "DB_PATH")},
                        "TESTING": True, "POD_NAME": "other-pod"})
    other_client = other.test_client()
    cookie = student.get_cookie("session")
    other_client.set_cookie("session", cookie.value)
    resp = other_client.post("/quiz/1/submit", data={})
    assert resp.status_code == 302
    html = other_client.get(resp.headers["Location"]).get_data(as_text=True)
    assert "other-pod" in html


def test_unknown_quiz_404(student):
    assert student.get("/quiz/999").status_code == 404
