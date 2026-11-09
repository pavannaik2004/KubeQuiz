# CONTEXT: single source of truth for progress

> **Rule:** read this file before starting any work, and append a log entry after finishing each piece of work.
> Related docs: [docs/PRD.md](docs/PRD.md) (what we are building) · [DECISIONS.md](DECISIONS.md) (decisions Claude made on the user's behalf)

## Current status
- **Phase:** All code written: M7 CI and M8 README done. The live-cluster verification of M3 to M6 is **still blocked on the user** running the WSL bootstrap. The CI e2e job will also verify the manifests once the repo is pushed to GitHub.
- **Last updated:** 2026-11-09 11:37 +05:30 (the phase line below is superseded by the 11:37 log entry: everything is deployed live and idempotent; the next step is the M5 scaling demo)
- **Next up:** (1) The user runs `bash scripts/wsl-bootstrap.sh` in WSL. (2) Run `site.yml` twice (deploy, then the idempotency check). (3) Run `scale-demo.yml` and tune the HPA/CPU if scaling is weak. (4) The user creates a GitHub repo and pushes, and CI goes green. (5) Screenshots for the report.

## Milestones
| # | Milestone | Status |
|---|-----------|--------|
| M0 | Plan, repo init, PRD / CONTEXT / DECISIONS | Done |
| M1 | Flask app + tests passing locally | Done |
| M2 | Dockerfile + docker-compose | Done |
| M3 | Kubernetes manifests on minikube | Written + schema-valid; not yet applied |
| M4 | Ansible automation (site / teardown / scale-demo) | Written + syntax/lint clean; not yet run |
| M5 | HPA + Locust in-cluster, scaling demonstrated | Manifests/playbook written; not yet run |
| M6 | Prometheus + Grafana dashboard | Written; not yet run |
| M7 | GitHub Actions CI | Written + actionlint clean; not yet run on GitHub |
| M8 | README, demo guide, report material | README done; screenshots pending a live run |

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

### 2026-11-09 09:46 | M2 | Docker image, compose and Locust
- `.gitattributes` (LF line endings, D-017).
- `app/gunicorn.conf.py`: gthread, 1 worker × 4 threads, 20 s graceful timeout for SIGTERM.
- `app/Dockerfile`: multi-stage python:3.12-slim, UID 10001, `/data` volume, urllib HEALTHCHECK (D-016). `app/.dockerignore`.
- `loadtest/locustfile.py`: `QuizTaker` user. It logs in with a random bot name, takes random quizzes with random answers, and sometimes opens the leaderboard (D-018).
- `docker-compose.yml`: app (AUTO_SEED, named volume) plus Locust under the `load` profile (D-019).
- Verified: the image `kubequiz:dev` builds at 206 MB; the container reports **healthy**; `/api/stats` shows 3 quizzes / 18 questions; `id` shows uid=10001. A headless Locust run of 30 users for 30 s made **882 requests with 0 failures**, median 4 ms, p95 28 ms.
- Environment: Docker Desktop 29.8.0 is running; its VM has 12 CPUs and about 8 GB RAM.

### 2026-11-09 10:07 | M3 / M4 / M6 | K8s manifests, Ansible, monitoring (offline-verified)
- **WSL findings:** Ubuntu 26.04 with Python 3.14 but **no pip or ensurepip**. `sudo` needs a password. docker and kubectl (Docker Desktop's) work. minikube, Helm and Ansible are missing. As a result, all installs go to user space (D-020, D-021).
- **Blocked:** running `scripts/wsl-bootstrap.sh` was **denied by the Claude Code auto-mode safety classifier** ("Unauthorized Persistence"; the script appended to `~/.bashrc` and used a curl-to-sh installer). The `~/.bashrc` edit has been removed from the script, which now only prints a PATH tip. **The user needs to run the bootstrap themselves or approve it.**
- `k8s/`: namespace, configmap, secret.example, pvc, db-init-job, deployment (no replicas field; probes; non-root; read-only root FS; preStop), service (NodePort 30080), hpa (3..10 @50%), `monitoring/servicemonitor.yaml`, `locust/locust.yaml` (master + 2 workers), `locust/headless-job.yaml` + `locust/demo-settings.yaml`.
- `ansible/`: `ansible.cfg`, `inventory.ini` (localhost), `requirements.yml` (kubernetes.core ≥6.6), `group_vars/all.yml`, `site.yml`, `teardown.yml`, `scale-demo.yml`; roles prereqs, cluster, build, deploy, monitoring (+ dashboard ConfigMap template), loadtest (+ shared `locustfile.yml`).
- `monitoring/values.yaml` (slim kube-prometheus-stack) and `monitoring/dashboard-kubequiz.json` (9 panels: replicas, req/s, HPA CPU, submissions/min, 5xx, replicas over time, CPU per pod, req/s per pod, p50/p95).
- `scripts/`: `wsl-bootstrap.sh`, `run-playbook.sh` (sets ANSIBLE_CONFIG because `/mnt/d` is world-writable), `port-forward.sh`, `watch-scaling.sh`.
- Tool versions checked live and pinned (D-027): minikube v1.39.0, K8s v1.37.0, Helm v3.22.1, chart 93.1.0, ansible-core 2.18.20, kubernetes py 37.0.2.
- **Verified offline:** kubeconform strict (schemas downloaded on the host because containers can't reach raw.githubusercontent.com): 13/13 valid, ServiceMonitor skipped (CRD). `ansible-playbook --syntax-check` passes for all 3 playbooks. `ansible-lint`: clean. shellcheck: clean. Dashboard JSON parses.
- **Mistake fixed:** a PowerShell bulk-replace flattened arrays and replaced every `-` with a space in `roles/loadtest/tasks/{main,locustfile}.yml`. Both files were rewritten in full, then re-linted clean.
- Decisions D-011 (revised) and D-020 to D-029 recorded.

### 2026-11-09 10:13 | M7 / M8 | CI pipeline, e2e smoke test, README
- Checked first: the WSL bootstrap had **still not been run** (uv, Ansible, minikube and Helm all missing), so I did the unblocked milestones.
- `.github/workflows/ci.yml`: jobs test, infra-lint, e2e (kind), publish (GHCR, main only) (D-030).
- `scripts/e2e-smoke.sh`: applies `k8s/` with kubectl, then checks the db-init Job, 3 ready replicas, in-cluster curl through the Service (readyz, stats, home page, metrics, 40× `/api/info` must reach ≥2 distinct pods), a 30 s / 20-user Locust Job with 0 failures, and attempts counted in the shared DB (D-031).
- `README.md`: requirement mapping, mermaid architecture, features, layout, compose quick start, the WSL + Ansible deploy, what each role does, the scaling demo script, teardown, testing/CI, design notes, troubleshooting, limitations, screenshot checklist.
- Verified: actionlint clean (after quoting `${APP_VERSION}`), shellcheck clean, pytest still 22 passed.
- **Blocked:** a local run of the e2e script on a temporary kind cluster was **denied by the auto-mode classifier** ("Code from External": downloading and running `kind.exe`). It was not worked around. The e2e script has therefore **not been executed yet**; it will run in CI on push, or locally if the user approves kind.

### 2026-11-09 10:20 | M5 (pre-tuning) | Measured CPU per request, retuned HPA inputs
- Checked first: the WSL bootstrap had still not been run, and there is no git remote.
- docker compose + Locust: 100 users for 60 s gave **5646 requests, 0 failures, 94.7 req/s, median 6 ms, avg 12 ms**. Container CPU sampled with `docker stats`: steady average **~34% of a core (~340m)**, so about **3.6m CPU per request**.
- Conclusion: at 100m/50%, 300 users would want about 20 pods and pin at the max of 10. Changed (D-032): pod CPU request **200m**, demo default **200 users** (expect about 7 pods). Updated `k8s/deployment.yaml`, `hpa.yaml` comment, `locust/demo-settings.yaml`, `group_vars`, the dashboard panel title, README, PRD N3 and success criteria (baseline 3, not 2), and D-011.
- Still to confirm on live minikube (M5).

### 2026-11-09 11:37 | M3 / M4 / M6 / M7 | LIVE: bootstrap, GitHub + CI green, site.yml green and idempotent
- With the user's approval, ran `scripts/wsl-bootstrap.sh` in WSL: uv, ansible-core 2.18.20 and kubernetes.core 6.6.0 installed.
- With the user's approval, created a **private** GitHub repo via gh: https://github.com/pavannaik2004/KubeQuiz (the user did not specify public or private, so I chose private as the reversible option). Pushed `main`.
- **CI run 42564326187: all 4 jobs succeeded.** e2e on kind: seeded 3 quizzes; `/api/info` answered by **3 distinct pods**; Locust 593 requests, Job completed (0 failures); **200 attempts** in the shared DB; image published to GHCR.
- **Live `site.yml` needed 6 attempts. Fixes:**
  1. GitHub release downloads were flaky (TLS handshake timeout, connection reset, repeated **504**). Added `timeout: 60` + retries; skip downloads when the versioned binary already exists; install the chart from **OCI `oci://ghcr.io/prometheus-community/charts/kube-prometheus-stack`** (D-033).
  2. minikube v1.39 defaults to **containerd**, so `minikube docker-env` failed (`moby/buildkit ... 404`). Now the image is built with Docker Desktop and copied in with `minikube image load` (D-012 revised).
  3. **Grafana OOMKilled** at a 256Mi limit; raised to 512Mi (request 256Mi) in `monitoring/values.yaml`.
- Then the idempotency check reported changed=3. Fixed (D-034): `--provenance=false --sbom=false` (the image ID was changing on every build), load only when the deployed annotation ID differs, Helm values inline instead of `values_files`.
- **Verified: two consecutive `site.yml` runs gave `ok=36 changed=0 failed=0`.** Cluster: quiz-app 3/3 Running, HPA `cpu: 0%/50%` (metrics-server OK), Prometheus/Grafana/operator/kube-state-metrics Running.
- Bumped the GitHub Actions to Node-24 majors (checkout/setup-python v7, buildx/login v4, metadata v6, build-push v7) after Node 20 deprecation warnings.
- Note: during debugging the image was rebuilt outside Ansible, so the image content in minikube is from an earlier build of the **same code**. The behaviour is identical; the next code change will load and roll normally.
