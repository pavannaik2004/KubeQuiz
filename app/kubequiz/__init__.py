"""KubeQuiz: a small online quiz platform built to run as many replicas on Kubernetes."""
import logging
import os
import socket

from flask import Flask

from . import db, metrics

__version__ = "1.0.0"

DEV_SECRET_KEY = "dev-only-change-me"


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        # Every replica MUST share the same SECRET_KEY: the login session is a
        # signed cookie, so a request can land on any pod and still be valid.
        SECRET_KEY=os.environ.get("SECRET_KEY", DEV_SECRET_KEY),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "admin"),
        DB_PATH=os.environ.get("DB_PATH", os.path.join(app.instance_path, "quiz.db")),
        DEFAULT_TIME_LIMIT=_env_int("QUIZ_TIME_LIMIT", 300),
        TIME_GRACE_SECONDS=_env_int("QUIZ_TIME_GRACE", 10),
        POD_NAME=os.environ.get("POD_NAME") or socket.gethostname(),
        APP_VERSION=os.environ.get("APP_VERSION", __version__),
        AUTO_SEED=os.environ.get("AUTO_SEED", "false").lower() == "true",
        METRICS_ENABLED=os.environ.get("METRICS_ENABLED", "true").lower() == "true",
    )
    if test_config:
        app.config.update(test_config)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    if app.config["SECRET_KEY"] == DEV_SECRET_KEY and not app.testing:
        app.logger.warning("SECRET_KEY not set: using the insecure development key")

    db.init_app(app)
    with app.app_context():
        conn = db.get_db()
        db.init_schema(conn)
        if app.config["AUTO_SEED"]:
            from .seed import seed_if_empty
            seed_if_empty(conn)

    from .routes import admin, api, health, quiz

    app.register_blueprint(health.bp)
    app.register_blueprint(quiz.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(api.bp)

    metrics.init_app(app)

    @app.context_processor
    def inject_pod_info():
        return {
            "pod_name": app.config["POD_NAME"],
            "app_version": app.config["APP_VERSION"],
        }

    return app
