def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json["pod"] == "test-pod"


def test_readyz(client):
    assert client.get("/readyz").status_code == 200


def test_readyz_fails_when_db_unusable(app, client, tmp_path):
    app.config["DB_PATH"] = str(tmp_path / "missing-dir" / "sub" / "x.db")
    # Fresh DB without schema -> "no such table" -> not ready.
    assert client.get("/readyz").status_code == 503


def test_api_info_and_stats(client):
    assert client.get("/api/info").json["pod"] == "test-pod"
    stats = client.get("/api/stats").json
    assert stats["quizzes"] == 3
    assert stats["questions"] > 0


def test_metrics_endpoint(client):
    client.get("/")
    body = client.get("/metrics").get_data(as_text=True)
    assert "flask_http_request_total" in body
    assert "kubequiz_app_info" in body
