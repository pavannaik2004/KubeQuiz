import re

import pytest

from kubequiz import create_app


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "ADMIN_PASSWORD": "s3cret",
        "DB_PATH": str(tmp_path / "quiz.db"),
        "AUTO_SEED": True,
        "POD_NAME": "test-pod",
    })
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def csrf_from(html):
    m = re.search(r'name="csrf" value="([^"]+)"', html)
    assert m, "no csrf token in page"
    return m.group(1)


@pytest.fixture
def admin_client(client):
    page = client.get("/admin/login").get_data(as_text=True)
    resp = client.post("/admin/login", data={"password": "s3cret", "csrf": csrf_from(page)})
    assert resp.status_code == 302
    return client


@pytest.fixture
def student(client):
    client.post("/login", data={"username": "Asha"})
    return client
