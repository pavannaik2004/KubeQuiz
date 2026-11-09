# CONTEXT: single source of truth for progress

> **Rule:** read this file before starting any work, and append a log entry after finishing each piece of work.
> Related docs: [docs/PRD.md](docs/PRD.md) (what we are building) · [DECISIONS.md](DECISIONS.md) (decisions Claude made on the user's behalf)

## Current status
- **Phase:** M1 done, M2 next
- **Last updated:** 2026-11-09 09:45 +05:30
- **Next up:** M2: Dockerfile (python:3.12-slim, non-root, gunicorn gthread) and docker-compose (app + Locust), plus `loadtest/locustfile.py`. Docker Desktop must be running.

## Milestones
| # | Milestone | Status |
|---|-----------|--------|
| M0 | Plan, repo init, PRD / CONTEXT / DECISIONS | Done |
| M1 | Flask app + tests passing locally | Done |
| M2 | Dockerfile + docker-compose | Not started |
| M3 | Kubernetes manifests on minikube | Not started |
| M4 | Ansible automation (site / teardown / scale-demo) | Not started |
| M5 | HPA + Locust in-cluster, scaling demonstrated | Not started |
| M6 | Prometheus + Grafana dashboard | Not started |
| M7 | GitHub Actions CI | Not started |
| M8 | README, demo guide, report material | Not started |

## Environment facts
- Windows 11 host. Docker Desktop is installed (with bundled kubectl). It was **stopped** at the 2026-11-09 check.
- WSL2: the `Ubuntu` distro exists (it was stopped). Ansible, minikube and Helm will be installed there.
- Python 3.12 and Node are on Windows; git identity is `pavannaik2004 <pavannaik2004@gmail.com>`.
- Commits must have **no Claude co-author or attribution**.

## Log
Newest entries go at the bottom. Format: `### YYYY-MM-DD HH:MM | <milestone> | <summary>`, then bullet points saying what changed.

### 2026-11-09 09:20 | M0 | Planning
- Read the project brief: Docker, K8s replicas, Ansible, HPA with simulated users.
- Checked the tooling: docker and kubectl present; minikube, Helm and Ansible missing; WSL Ubuntu available.
- The user chose Flask+SQLite, minikube, Locust, Prometheus+Grafana, CI and an admin page.
- Plan approved (saved at `C:\Users\pavan\.claude\plans\i-have-to-do-async-parasol.md`).

### 2026-11-09 09:30 | M0 / M1 | Repo init and app core
- `git init -b main` and added `.gitignore`.
- `app/requirements.txt`, `app/requirements-dev.txt`.
- `app/kubequiz/schema.sql`: tables quizzes, questions and attempts (attempts store answers as JSON).
- `app/kubequiz/db.py`: SQLite access with WAL and busy_timeout, plus every query helper.
- `app/kubequiz/scoring.py`: pure scoring and form parsing.
- `app/kubequiz/__init__.py`: `create_app()` factory, configured from env vars; shows the pod name in each page.
- `app/kubequiz/metrics.py`: Prometheus exporter plus quiz counters, using a registry per app.
- `app/kubequiz/routes/`: `health` (/healthz, /readyz), `quiz` (student flow), `admin` (CRUD + CSRF), `api` (/api/info, /api/quizzes, /api/stats).

### 2026-11-09 09:40 | M0 | Project docs
- Added `docs/PRD.md`, `CONTEXT.md` (this file) and `DECISIONS.md` (D-001 to D-015), at the user's request.

### 2026-11-09 09:45 | M1 | Flask app finished and tested
- `app/kubequiz/seed.py`: 3 sample quizzes (Kubernetes 7 questions, Docker 5, DevOps/Ansible 6). `BEGIN IMMEDIATE` stops two seeders racing. Runs as `python -m kubequiz.seed`.
- Templates: base, index, quiz (timer), result (review), leaderboard, admin/login, admin/dashboard, admin/edit_quiz. Static: `style.css` (light and dark), `timer.js` (submits automatically at 0).
- Tests: `app/tests/`, 22 tests covering scoring, the quiz flow, late submission, statelessness across two app instances, admin CRUD + CSRF, health, API and metrics. Run with: `cd app; .\.venv\Scripts\python -m pytest`.
- **Bug fixed:** the CSRF check passed when the session had no token, because an empty value matched the empty default. Requests are now rejected when no session token exists.
- Verified: `pytest` 22 passed; `flake8` clean; seed run twice (second run skipped; DB in WAL mode; 3 quizzes / 18 questions).
- Dev venv at `app/.venv` (gitignored).
