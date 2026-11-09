#!/usr/bin/env bash
# Live view of the autoscaler while a load test runs.
#   bash scripts/watch-scaling.sh
export PATH="$HOME/.local/bin:$PATH"
exec watch -n 2 '
  kubectl -n kubequiz get hpa quiz-app
  echo
  kubectl -n kubequiz top pods -l app.kubernetes.io/component=web 2>/dev/null
  echo
  kubectl -n kubequiz get pods -l app.kubernetes.io/component=web -o wide
'
