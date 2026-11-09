#!/usr/bin/env bash
# Record an HPA timeline (CSV) while a load test runs, e.g. for the report.
#   bash scripts/record-scaling.sh [seconds=600] [interval=20] > scaling.csv
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"
duration="${1:-600}"
interval="${2:-20}"
start=$(date +%s)
echo "elapsed_s,current_replicas,desired_replicas,cpu_utilization_pct,ready_pods"
while [ $(( $(date +%s) - start )) -le "$duration" ]; do
  hpa=$(kubectl -n kubequiz get hpa quiz-app -o jsonpath='{.status.currentReplicas},{.status.desiredReplicas},{.status.currentMetrics[0].resource.current.averageUtilization}' 2>/dev/null)
  ready=$(kubectl -n kubequiz get deploy quiz-app -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
  echo "$(( $(date +%s) - start )),${hpa},${ready}"
  sleep "$interval"
done
