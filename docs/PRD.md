# KubeQuiz: Product Requirements Document

| | |
|---|---|
| Project | DevOps Project 7: Kubernetes-Based Online Quiz System |
| Version | 1.0 |
| Date | 2026-11-09 |
| Status | In development |

## 1. Problem statement
In an online exam, many students tend to log in at the same moment, for example when the exam opens. A platform sized for average load slows down or fails at that point, while one sized for the peak wastes resources the rest of the time. We need a quiz platform that:
- runs as several identical copies, so that one failure does not take it down
- adds copies automatically when load rises and removes them when it falls
- can be deployed again from nothing with a single command

## 2. Goals
| # | Goal | Requirement it covers |
|---|------|------------------------|
| G1 | Package the quiz application as a Docker container image | Docker |
| G2 | Run the app on Kubernetes with several replicas behind one Service | Kubernetes |
| G3 | Automate the whole deployment (cluster, image, app, monitoring) with Ansible | Ansible |
| G4 | Scale replicas automatically (HPA) under load from simulated users | Extension |
| G5 | Make the scaling visible: live dashboards and the pod that served each request | Demo / evaluation |

## 3. Non-goals
- Production-grade multi-node storage. SQLite on a shared volume is acceptable on single-node minikube; see DECISIONS.md.
- Real user accounts, passwords for students, email or SSO. Students enter only a display name.
- Question types other than single-choice MCQ.
- Proctoring and anti-cheating beyond a server-side time limit.
- Cloud deployment (EKS/GKE). Local minikube only.

## 4. Users
| Persona | Needs |
|---------|-------|
| Student (exam taker) | Enter a name, pick a quiz, answer within the time limit, see the score and the correct answers, see the leaderboard |
| Admin (teacher) | Log in with a password; create, edit and delete quizzes; add and delete questions; see totals |
| Operator (DevOps engineer, i.e. us) | Deploy with one command, watch health and scaling, run load tests, tear everything down |

## 5. Functional requirements

### 5.1 Quiz application
| ID | Requirement |
|----|-------------|
| F1 | The home page lists every quiz with its question count and time limit |
| F2 | A student enters a display name (2-32 characters) before starting a quiz |
| F3 | The quiz page shows all questions with a countdown timer and submits automatically at zero |
| F4 | The server enforces the time limit (plus a short grace period), so a late submission scores 0 |
| F5 | The result page shows the score, the time taken and a review of each question (chosen vs correct) |
| F6 | Each quiz has a leaderboard of the top 10, ranked by score and then by fastest time |
| F7 | Every page footer shows the pod that served it, to demonstrate load balancing |
| F8 | Admin login is protected by a password from a Kubernetes Secret; admin forms are CSRF-protected |
| F9 | The admin can create, edit and delete quizzes and add or delete questions (2-6 options, one correct) |
| F10 | JSON API: `/api/info` (serving pod), `/api/quizzes`, `/api/stats` |
| F11 | Sample quizzes are seeded on first deployment (Kubernetes, Docker, DevOps/Ansible) |

### 5.2 Platform and DevOps
| ID | Requirement |
|----|-------------|
| D1 | Docker image: slim Python base, runs as a non-root user, has a HEALTHCHECK, served by gunicorn |
| D2 | docker-compose for local development (app + Locust) |
| D3 | Kubernetes resources: Namespace, ConfigMap, Secret, PVC, a db-init Job, a Deployment (3 replicas), a Service and an HPA |
| D4 | Liveness probe `/healthz` and readiness probe `/readyz` (checks that the DB is reachable) |
| D5 | Each pod declares resource requests and limits, which the HPA needs for its CPU math |
| D6 | HPA: minimum 2, maximum 10 replicas, 50% CPU target, fast scale-down for the demo |
| D7 | Ansible playbook `site.yml` installs the prerequisites, starts minikube, builds the image, deploys the app, monitoring and Locust; it is idempotent |
| D8 | Ansible playbooks `teardown.yml` (clean up) and `scale-demo.yml` (runs the load ramp) |
| D9 | Locust simulates students (open a quiz, answer, submit, view the leaderboard) and runs inside the cluster |
| D10 | Prometheus scrapes `/metrics`; a Grafana dashboard shows replicas, CPU per pod, request rate, p95 latency and errors |
| D11 | GitHub Actions CI: lint, unit tests, image build, Kubernetes manifest validation, push to GHCR on main |

## 6. Non-functional requirements
| ID | Requirement |
|----|-------------|
| N1 | Stateless pods: any replica can serve any request, because sessions are signed cookies shared via SECRET_KEY |
| N2 | No downtime when a pod is killed (at least 2 replicas at all times, readiness gating) |
| N3 | Under about 200 simulated users, the HPA scales up within about 2 minutes and the error rate stays under 1% |
| N4 | A full deployment from a clean WSL install finishes with one bootstrap script plus one playbook |
| N5 | Secrets are never baked into the image; they are injected through a Kubernetes Secret |

## 7. Architecture (summary)
```
Browser ─► Service (NodePort) ─► quiz-app pods (2..10, HPA) ─► PVC (SQLite, WAL)
Locust master/workers ─► Service          Prometheus ─► /metrics ─► Grafana
Ansible (WSL, local connection) ─► minikube: builds the image and applies everything
```
The full design is in the README.

## 8. Success criteria (demo checklist)
1. `ansible-playbook site.yml` runs green twice; the second run changes nothing in the deploy role.
2. `kubectl get pods` shows 3 healthy replicas, and refreshing the page shows different pod names.
3. Deleting a pod causes no user-visible outage, and Kubernetes recreates it.
4. A Locust ramp to 200 users scales replicas from 3 to at least 5 (about 7 expected), and this shows in `kubectl get hpa -w` and in Grafana.
5. When the load stops, replicas return to 3.
6. CI is green on GitHub.

## 9. Milestones
| # | Milestone |
|---|-----------|
| M1 | Flask app, tests passing locally |
| M2 | Docker image and docker-compose |
| M3 | Kubernetes manifests running on minikube |
| M4 | Ansible automation from start to finish |
| M5 | HPA and Locust, scaling demonstrated |
| M6 | Prometheus/Grafana dashboard |
| M7 | GitHub Actions CI |
| M8 | README, demo guide and report material |

## 10. Risks
| Risk | Mitigation |
|------|------------|
| SQLite write contention under load | WAL mode, busy_timeout, short transactions, a metric counting DB errors |
| Laptop RAM too small for the monitoring stack | Slimmed Helm values; `enable_monitoring: false` toggle |
| HPA shows `<unknown>` targets | Enable metrics-server and set CPU requests on the pods |
| Windows/WSL networking quirks | Port-forward script binding to 0.0.0.0, reachable from Windows via localhost |
