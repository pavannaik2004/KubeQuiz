"""Prometheus metrics.

prometheus_flask_exporter adds request count/latency metrics for every route
and serves them on /metrics. On top of that we track quiz-specific counters.

Each app gets its own CollectorRegistry, so tests can build many apps without
"duplicated timeseries" errors.
"""
from flask import current_app
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram
from prometheus_flask_exporter import PrometheusMetrics


class QuizMetrics:
    def __init__(self, registry):
        self.attempts_started = Counter(
            "kubequiz_attempts_started_total",
            "Quizzes opened by a user",
            ["quiz_id"],
            registry=registry,
        )
        self.submissions = Counter(
            "kubequiz_submissions_total",
            "Quiz answer sheets submitted",
            ["quiz_id"],
            registry=registry,
        )
        self.score_ratio = Histogram(
            "kubequiz_score_ratio",
            "Score as a fraction of the maximum (0..1)",
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=registry,
        )
        self.db_errors = Counter(
            "kubequiz_db_errors_total",
            "Database operations that failed (e.g. lock timeouts)",
            registry=registry,
        )
        self.up = Gauge(
            "kubequiz_up",
            "1 while this replica is serving",
            registry=registry,
        )
        self.up.set(1)


class _NoopMetric:
    def labels(self, *_a, **_k):
        return self

    def inc(self, *_a, **_k):
        pass

    def observe(self, *_a, **_k):
        pass

    def set(self, *_a, **_k):
        pass


class _NoopQuizMetrics:
    attempts_started = submissions = score_ratio = db_errors = up = _NoopMetric()


def init_app(app):
    if not app.config.get("METRICS_ENABLED", True):
        app.extensions["kubequiz_metrics"] = _NoopQuizMetrics()
        return
    registry = CollectorRegistry(auto_describe=True)
    exporter = PrometheusMetrics(
        app,
        registry=registry,
        group_by="url_rule",            # /quiz/<int:quiz_id>, not one series per id
        excluded_paths=["/healthz", "/readyz", "/metrics", "/static"],
    )
    exporter.info(
        "kubequiz_app_info",
        "Application build info",
        version=app.config["APP_VERSION"],
        pod=app.config["POD_NAME"],
    )
    app.extensions["kubequiz_metrics"] = QuizMetrics(registry)


def get():
    return current_app.extensions["kubequiz_metrics"]
