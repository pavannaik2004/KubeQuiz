# Decisions

These are decisions **Claude made on the user's behalf** while building KubeQuiz. Choices the user made explicitly are listed at the top for reference only.
To change one, say so and update its entry: set the status to `Reversed` and add a note.

## Decided by the user
- App stack: Flask + SQLite
- Cluster: minikube
- Load generator: Locust
- Extras: Prometheus + Grafana, GitHub Actions CI, admin page
- No Claude co-author or attribution in commits or PRs

---

## Format
`D-NNN | date | area`: **Decision**. *Why.* Alternatives considered. Status.

---

### D-001 | 2026-11-09 | Platform
**Run Ansible and minikube inside WSL2 Ubuntu, using Docker Desktop through its WSL integration.**
*Why:* Ansible does not run natively on Windows as a control node. WSL Ubuntu already exists on this machine.
Alternatives: an Ansible container, or a Linux VM. Status: Active.

### D-002 | 2026-11-09 | Storage
**All replicas share a single SQLite file on one PVC (minikube's hostPath `standard` StorageClass). SQLite runs in WAL mode with `busy_timeout=5000` and `synchronous=NORMAL`.**
*Why:* The user chose SQLite. A single-node cluster lets every pod mount the same RWO volume, and WAL allows concurrent readers alongside one writer.
Alternatives: SQLite per pod (breaks shared state), Postgres (rejected by the user). Status: Active. *Limitation:* this does not work on a multi-node cluster. The README documents it.

### D-003 | 2026-11-09 | App
**No student accounts. A student enters only a display name, which is stored in a signed Flask session cookie.**
*Why:* Keeps the pods stateless (any replica can serve any request) and keeps the project focused on DevOps.
Alternatives: accounts stored in the DB, or server-side sessions in Redis. Status: Active.

### D-004 | 2026-11-09 | App
**The quiz start time is stored in the signed session cookie, not in the DB. The server enforces the limit as `time_limit + 10s` grace; a late submission scores 0.**
*Why:* Start and submit can land on different pods, and the cookie travels with the user. It also avoids one DB write per quiz opened.
Alternatives: an `attempts` row created at start. Status: Active.

### D-005 | 2026-11-09 | App
**SECRET_KEY must be identical on all replicas and comes from a Kubernetes Secret. The app logs a warning when it falls back to the dev key.**
*Why:* With a random key per pod, a cookie signed by one pod would be rejected by the others.
Status: Active.

### D-006 | 2026-11-09 | App
**Answers are stored as JSON in `attempts.answers`, so the result page can rebuild the per-question review.**
*Why:* One row per attempt, with no answers table. Simple, and enough for the review page.
Status: Active.

### D-007 | 2026-11-09 | Security
**CSRF tokens protect admin forms only. Student quiz forms carry no CSRF token.**
*Why:* The admin actions are the destructive ones. Leaving the token off student forms keeps the Locust script simple, because it does not have to parse a token.
Alternatives: Flask-WTF on every form. Status: Active.

### D-008 | 2026-11-09 | Metrics
**`prometheus_flask_exporter` with `group_by="url_rule"` and a dedicated CollectorRegistry per app. Probe and metrics paths are excluded from the metrics.**
*Why:* `url_rule` avoids one time series per quiz id. A per-app registry stops tests from hitting "duplicated timeseries" errors. Excluding the probes keeps the request rate showing only real traffic.
Status: Active.

### D-009 | 2026-11-09 | Runtime
**Gunicorn runs 1 worker process with `gthread` and 4 threads per pod.**
*Why:* With a single process, Prometheus metrics need no multiprocess mode. Small pods make CPU climb, which makes HPA scaling visible.
Status: Active.

### D-010 | 2026-11-09 | Kubernetes
**A db-init Job seeds the schema and data before the Deployment rolls out. The app also runs `CREATE TABLE IF NOT EXISTS` at startup, which is harmless.**
*Why:* Prevents several replicas racing to seed the database at the same time.
Status: Active.

### D-011 | 2026-11-09 | Kubernetes
**HPA: minimum 2, maximum 10 replicas, 50% CPU target, 60s scale-down stabilization. Pods request cpu=100m, mem=128Mi.**
*Why:* At least 2 replicas keeps high availability. The short stabilization window lets the demo show the scale-down within minutes; the default is 5 minutes.
Status: Active (may be tuned in M5).

### D-012 | 2026-11-09 | Build
**Images are built straight into minikube's Docker daemon (`minikube docker-env`) with `imagePullPolicy: IfNotPresent`. CI separately pushes to GHCR.**
*Why:* Needs no registry or credentials locally, and the local loop is faster.
Status: Active.

### D-013 | 2026-11-09 | Service
**A NodePort Service, reached through `kubectl port-forward` from WSL so it is available on Windows at localhost.**
*Why:* With the docker driver on WSL, NodePorts are not directly reachable from Windows. An Ingress adds complexity the user did not ask for.
Status: Active.

### D-014 | 2026-11-09 | Admin
**The default admin password for local dev is `admin`. In Kubernetes it comes from a Secret whose value is set in Ansible `group_vars`.**
*Why:* Easy for a demo, and configurable. Status: Active.

### D-015 | 2026-11-09 | Docs
**Location of the project docs: `docs/PRD.md`, `CONTEXT.md` (progress log) and `DECISIONS.md` (this file).**
Status: Active.

### D-016 | 2026-11-09 | Docker
**Multi-stage image (a build stage creates a venv; the runtime stage copies only the venv and the code). It runs as fixed UID/GID 10001, and the HEALTHCHECK uses python's urllib because curl is not in the slim image.**
*Why:* A smaller image without build tooling, and the fixed UID lets the K8s `securityContext`/`fsGroup` give the pod write access to the PVC.
Status: Active.

### D-017 | 2026-11-09 | Repo
**`.gitattributes` forces LF line endings (except `.bat`/`.ps1`).**
*Why:* The repo is edited on Windows but its scripts run in WSL, containers and CI, where CRLF line endings break bash and shebang lines.
Status: Active.

### D-018 | 2026-11-09 | Load test
**Locust is pinned to `locustio/locust:2.31.8`. The simulated user mix: browse 1, take quiz 4 (open, answer randomly, submit, sometimes the leaderboard), /api/info 1; wait 1-3 s between tasks.**
*Why:* Taking quizzes dominates, as it would in a real exam. The pinned version makes runs reproducible.
Status: Active.

### D-019 | 2026-11-09 | Compose
**docker-compose runs a single app replica. Locust sits behind the `load` profile, so it starts only when asked.**
*Why:* Compose is only for local development. Replicas and scaling are demonstrated on Kubernetes.
Status: Active.
