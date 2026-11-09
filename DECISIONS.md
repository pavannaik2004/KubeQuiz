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
**HPA: minimum 3, maximum 10 replicas, 50% CPU target, scale-up immediately (+100% or +4 pods per 15s), 60s scale-down stabilization. Pods request cpu=200m (was 100m, see D-032), mem=128Mi. The Deployment has no `replicas:` field; the HPA owns it.**
*Why:* 3 replicas is the "multiple replicas" baseline. A fixed `replicas` in the Deployment would be reset on every `apply` and fight the HPA. The short stabilization window lets the demo show the scale-down within minutes; the default is 5 minutes.
Status: Active (revised 2026-11-09: min was 2; may be tuned in M5).

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

### D-020 | 2026-11-09 | Ansible
**Everything on the control node installs in user space with no sudo. minikube, kubectl and helm go to `~/.local/share/kubequiz-tools/<tool>-<version>`, symlinked into `~/.local/bin`. The Ansible roles use no `become`.**
*Why:* sudo in WSL needs a password, which breaks unattended runs. Versioned files plus symlinks make version bumps clean and re-runs no-ops.
Status: Active.

### D-021 | 2026-11-09 | Ansible
**Ansible is installed with `uv tool install` (ansible-core 2.18.20 on a uv-managed Python 3.12, plus the `kubernetes` client 37.0.2). The inventory uses `ansible_python_interpreter={{ ansible_playbook_python }}`.**
*Why:* Ubuntu 26.04 in WSL has Python 3.14 without `ensurepip`/pip, so the usual venv or pip route does not work without apt. uv is a single binary. ansible-core 2.22 would need Python ≥3.13, and 2.18 is a stable LTS-like line.
Status: Active.

### D-022 | 2026-11-09 | Deploy
**The image tag stays fixed (`kubequiz:1.0.0`). The deploy role stamps the pod template with the annotation `kubequiz/image-id: <docker image ID>`, so a changed build triggers a rolling update and an unchanged build changes nothing.**
*Why:* Builds go straight into minikube without a registry, so retagging every build isn't needed. Docker's layer cache gives a stable image ID, which keeps the playbook idempotent.
Status: Active.

### D-023 | 2026-11-09 | Deploy
**The db-init Job is created only if it does not exist (k8s_info, then create). It is never re-applied.**
*Why:* Job pod templates are immutable, so re-applying after an image change fails. The seed only needs to run once per volume, and the seeder is idempotent anyway.
Status: Active.

### D-024 | 2026-11-09 | Load test
**The locustfile ConfigMap is generated by Ansible from `loadtest/locustfile.py`, and the same file is used by compose. Locust pods restart when the file's SHA1 changes (pod-template annotation).**
*Why:* Keeps a single copy of the load script.
Status: Active.

### D-025 | 2026-11-09 | Load test
**The scale demo is a headless Locust Job. Its numbers come from the `locust-demo` ConfigMap as `LOCUST_*` env vars. `scale-demo.yml` writes the ConfigMap, starts the Job, waits for the HPA to reach `demo_expect_replicas` (5), prints the Locust summary, then waits for scale-in.**
*Why:* Unattended and repeatable (no clicking in the Locust UI and no port-forward needed by Ansible). The Job manifest never changes. The Locust master/worker pair stays available for interactive demos.
Status: Active.

### D-026 | 2026-11-09 | Monitoring
**Slim kube-prometheus-stack: no Alertmanager, no node-exporter, no control-plane scrapes, no default rules or dashboards. `serviceMonitorSelectorNilUsesHelmValues: false`. The Grafana sidecar loads our dashboard from a ConfigMap labelled `grafana_dashboard` and sets it as the home dashboard.**
*Why:* Fits in the laptop memory budget and avoids red targets that cannot work in minikube. The selector change lets Prometheus see the ServiceMonitor in the `kubequiz` namespace.
Status: Active.

### D-027 | 2026-11-09 | Versions
**Pinned: minikube v1.39.0, Kubernetes/kubectl v1.37.0 (minikube's default), Helm v3.22.1 (latest Helm 3, not Helm 4), kube-prometheus-stack chart 93.1.0, kubernetes.core ≥6.6 <7, Locust 2.31.8.**
*Why:* Reproducible runs. These were checked on 2026-11-09 against GitHub, PyPI and Galaxy and are mutually compatible. Helm 4 was avoided because kubernetes.core.helm targets the Helm 3 CLI. Locust stays at the version load-tested in M2.
Status: Active.

### D-028 | 2026-11-09 | minikube
**minikube runs with 4 CPUs and 4600 MB of RAM.**
*Why:* The Docker Desktop VM has about 8 GB in total, and Docker needs headroom. With monitoring (~1.2 GB), up to 10 app pods (256Mi limits) and Locust, this fits. If memory gets tight, use `enable_monitoring=false`.
Status: Active.

### D-030 | 2026-11-09 | CI
**GitHub Actions runs four jobs: `test` (flake8 + pytest), `infra-lint` (kubeconform strict, Ansible syntax-check + ansible-lint, shellcheck, dashboard JSON), `e2e` (builds the image, creates a kind cluster, runs `scripts/e2e-smoke.sh`) and `publish` (GHCR push on `main` only, tags `1.0.0`, `sha-<short>` and `latest`, using `GITHUB_TOKEN`).**
*Why:* The e2e job deploys the real manifests on a real cluster in every run, including a Locust run that must have zero failures. CI uses kind rather than minikube because it starts faster on runners; the manifests are the same. GHCR needs no extra secrets.
Status: Active.

### D-031 | 2026-11-09 | Testing
**The e2e smoke test is one script (`scripts/e2e-smoke.sh`), used by CI and runnable by hand on any fresh cluster.** It applies the plain `k8s/` files with kubectl, not Ansible, so it tests the manifests independently of the automation.
Status: Active.

### D-032 | 2026-11-09 | Autoscaling tuning
**The pod CPU request was raised from 100m to 200m, keeping the 50% HPA target. The default demo load went from 300 to 200 simulated users.**
*Why (measured):* a docker-compose run with 100 Locust users gave **94.7 req/s at about 340m CPU (about 3.6m per request)** with 0 failures. At 100m/50%, one pod saturates at about 14 req/s, so even 50 users would ask for 4 pods and 300 users for about 20, pinning the demo at the 10-pod cap. At 200m/50% it is about 1 pod per 30 users: 200 users gives about 7 pods, showing replicas tracking the load. Capacity check: 10 × 200m = 2 cores, which fits in minikube's 4 CPUs after the control plane (~0.85), monitoring (~0.22) and Locust (~0.45) requests.
Status: Active (re-check against the live minikube numbers in M5).

### D-029 | 2026-11-09 | Deploy
**Ansible applies the plain files in `k8s/` (`kubernetes.core.k8s src:`), except the Secret, which it builds from group_vars. `k8s/secret.example.yaml` is only for manual `kubectl` use.**
*Why:* `k8s/` stays usable with plain `kubectl apply`, and no real secret values live there.
Status: Active.
