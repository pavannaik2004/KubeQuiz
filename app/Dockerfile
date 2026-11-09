# syntax=docker/dockerfile:1

# ---- build stage: install dependencies into a virtualenv -----------------
FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /venv
COPY requirements.txt .
RUN /venv/bin/pip install -r requirements.txt

# ---- runtime stage: only the venv and the app code -----------------------
FROM python:3.12-slim
ARG APP_VERSION=1.0.0
LABEL org.opencontainers.image.title="kubequiz" \
      org.opencontainers.image.description="Scalable online quiz platform" \
      org.opencontainers.image.version="${APP_VERSION}"

ENV PATH="/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION} \
    DB_PATH=/data/quiz.db \
    PORT=8080

# Fixed non-root UID/GID so Kubernetes securityContext/fsGroup can match it.
RUN groupadd --gid 10001 app \
 && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
 && mkdir -p /data && chown app:app /data

COPY --from=build /venv /venv
WORKDIR /srv
COPY gunicorn.conf.py .
COPY kubequiz ./kubequiz

USER 10001
VOLUME ["/data"]
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2); sys.exit(0)"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "kubequiz:create_app()"]
