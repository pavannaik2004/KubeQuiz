#!/usr/bin/env bash
# End-to-end smoke test of the plain manifests in k8s/ on a *fresh, throwaway*
# cluster (kind in CI). Expects the image kubequiz:1.0.0 to be loaded already.
#
# Checks: db-init Job completes, HPA brings the app to 3 ready replicas,
# health/API work, the Service spreads requests over several pods, and a
# short Locust run (the real locustfile) finishes with zero failures.
#
#   bash scripts/e2e-smoke.sh
set -euo pipefail

NS=kubequiz
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K8S="$ROOT/k8s"

step() { printf '\n==> %s\n' "$*"; }
fail() { echo "FAIL: $*" >&2; dump; exit 1; }
dump() {
  echo "---- diagnostics ----"
  kubectl -n "$NS" get all,pvc,hpa 2>/dev/null || true
  kubectl -n "$NS" describe pods 2>/dev/null | tail -60 || true
  kubectl -n "$NS" logs -l app.kubernetes.io/component=web --tail=30 2>/dev/null || true
}

step "Apply namespace, config, secret, volume"
kubectl apply -f "$K8S/namespace.yaml"
kubectl apply -f "$K8S/configmap.yaml" -f "$K8S/secret.example.yaml" -f "$K8S/pvc.yaml"

step "Seed the database (db-init Job)"
kubectl apply -f "$K8S/db-init-job.yaml"
kubectl -n "$NS" wait --for=condition=complete job/quiz-db-init --timeout=240s \
  || fail "db-init job did not complete"
kubectl -n "$NS" logs job/quiz-db-init

step "Deploy app, service, HPA"
kubectl apply -f "$K8S/deployment.yaml" -f "$K8S/service.yaml" -f "$K8S/hpa.yaml"
kubectl -n "$NS" rollout status deploy/quiz-app --timeout=240s || fail "rollout failed"

step "Wait for HPA minReplicas (3 ready pods)"
for _ in $(seq 1 60); do
  ready="$(kubectl -n "$NS" get deploy quiz-app -o jsonpath='{.status.readyReplicas}')"
  [ "${ready:-0}" -ge 3 ] && break
  sleep 3
done
[ "${ready:-0}" -ge 3 ] || fail "only ${ready:-0} ready replicas"
kubectl -n "$NS" get pods -o wide

step "In-cluster requests through the Service"
# shellcheck disable=SC2016  # the script runs inside the curl pod, not here
kubectl -n "$NS" run smoke-curl --image=curlimages/curl:8.11.1 --restart=Never --quiet \
  --command -- sh -c '
    set -e
    curl -fsS http://quiz-app/readyz; echo
    curl -fsS http://quiz-app/api/stats; echo
    curl -fsS http://quiz-app/ | grep -q "Kubernetes Basics"
    curl -fsS http://quiz-app/metrics | grep -q flask_http_request_total
    for i in $(seq 1 40); do curl -fsS http://quiz-app/api/info; echo; done
  ' >/dev/null
kubectl -n "$NS" wait --for=jsonpath='{.status.phase}'=Succeeded pod/smoke-curl --timeout=120s \
  || { kubectl -n "$NS" logs smoke-curl || true; fail "smoke requests failed"; }
out="$(kubectl -n "$NS" logs smoke-curl)"
echo "$out" | head -2
pods="$(echo "$out" | grep -o '"pod":"[^"]*"' | sort -u | wc -l)"
echo "distinct pods that answered /api/info: $pods"
[ "$pods" -ge 2 ] || fail "requests were not load-balanced across pods"
kubectl -n "$NS" delete pod smoke-curl --wait=false

step "Short Locust run with the real locustfile (must have 0 failures)"
kubectl -n "$NS" create configmap locustfile --from-file="$ROOT/loadtest/locustfile.py" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create configmap locust-demo \
  --from-literal=LOCUST_HOST=http://quiz-app.$NS.svc.cluster.local \
  --from-literal=LOCUST_USERS=20 --from-literal=LOCUST_SPAWN_RATE=10 \
  --from-literal=LOCUST_RUN_TIME=30s \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f "$K8S/locust/headless-job.yaml"
# Locust exits non-zero if any request failed, which fails the Job.
if ! kubectl -n "$NS" wait --for=condition=complete job/locust-headless --timeout=240s; then
  kubectl -n "$NS" logs job/locust-headless --tail=40 || true
  fail "locust job failed (request failures?)"
fi
kubectl -n "$NS" logs job/locust-headless --tail=14

step "Attempts were stored in the shared database"
kubectl -n "$NS" exec deploy/quiz-app -- python -c \
  "import sqlite3; print('attempts:', sqlite3.connect('/data/quiz.db').execute('select count(*) from attempts').fetchone()[0])"

printf '\nE2E SMOKE TEST PASSED\n'
