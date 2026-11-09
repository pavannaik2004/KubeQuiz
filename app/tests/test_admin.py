from conftest import csrf_from


def test_admin_requires_login(client):
    resp = client.get("/admin/")
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]


def test_wrong_password(client):
    page = client.get("/admin/login").get_data(as_text=True)
    resp = client.post("/admin/login", data={"password": "nope", "csrf": csrf_from(page)})
    assert resp.status_code == 200
    assert "Wrong password" in resp.get_data(as_text=True)


def test_post_without_csrf_rejected(client):
    resp = client.post("/admin/login", data={"password": "s3cret"})
    assert resp.status_code == 400


def test_create_quiz_add_question_and_take_it(admin_client):
    page = admin_client.get("/admin/").get_data(as_text=True)
    token = csrf_from(page)
    resp = admin_client.post("/admin/quizzes", data={
        "csrf": token, "title": "Helm", "description": "charts", "time_limit_seconds": "120",
    })
    assert resp.status_code == 302
    edit_url = resp.headers["Location"]
    quiz_id = int(edit_url.rstrip("/").split("/")[-1])

    resp = admin_client.post(f"/admin/quizzes/{quiz_id}/questions", data={
        "csrf": token, "text": "Helm packages are called?",
        "option": ["charts", "pods", "", ""], "correct": "0",
    })
    assert resp.status_code == 302
    html = admin_client.get(edit_url).get_data(as_text=True)
    assert "Helm packages are called?" in html

    # The new quiz is playable.
    admin_client.post("/login", data={"username": "Teacher"})
    assert admin_client.get(f"/quiz/{quiz_id}").status_code == 200


def test_invalid_question_rejected(admin_client):
    token = csrf_from(admin_client.get("/admin/").get_data(as_text=True))
    admin_client.post("/admin/quizzes/1/questions", data={
        "csrf": token, "text": "only one option", "option": ["a"], "correct": "0",
    })
    html = admin_client.get("/admin/quizzes/1").get_data(as_text=True)
    assert "only one option" not in html


def test_delete_quiz(admin_client):
    token = csrf_from(admin_client.get("/admin/").get_data(as_text=True))
    admin_client.post("/admin/quizzes/3/delete", data={"csrf": token})
    assert admin_client.get("/admin/quizzes/3").status_code == 404
