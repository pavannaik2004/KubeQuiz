"""Gunicorn settings (see DECISIONS.md D-009).

One worker process with several threads: Prometheus metrics stay simple (no
multiprocess mode) and the pod's CPU use maps cleanly onto the HPA target.
"""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
workers = int(os.environ.get("GUNICORN_WORKERS", "1"))
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = 30
graceful_timeout = 20       # finish in-flight requests when Kubernetes sends SIGTERM
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
