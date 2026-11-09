#!/usr/bin/env bash
# Open tunnels from WSL to the cluster services. WSL2 forwards localhost to
# Windows, so these URLs also work in your Windows browser. Ctrl+C closes all.
#
#   bash scripts/port-forward.sh
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"

pids=()
forward() {  # namespace service local:remote label
  if kubectl -n "$1" get svc "$2" >/dev/null 2>&1; then
    kubectl -n "$1" port-forward --address 0.0.0.0 "svc/$2" "$3" >/dev/null 2>&1 &
    pids+=($!)
    echo "  $4  ->  http://localhost:${3%%:*}"
  fi
}

echo "Port-forwards (Ctrl+C to stop):"
forward kubequiz   quiz-app           8080:80   "App     "
forward kubequiz   locust-master      8089:8089 "Locust  "
forward monitoring monitoring-grafana 3000:80   "Grafana "
forward monitoring monitoring-kube-prometheus-prometheus 9090:9090 "Prometheus"

trap 'kill "${pids[@]}" 2>/dev/null; exit 0' INT TERM
wait
