#!/usr/bin/env bash

# Load/performance tests script that supports two modes:
# - local: tests against docker-compose stack (default)
# - staging: tests against deployed staging environment

set -euo pipefail

echo "[load-tests] Starting load test suite in $ENV mode..."

if [[ "$ENV" == "staging" ]]; then
  echo "[load-tests] Testing against staging at: $API_BASE_URL"
  # TODO: implement staging load tests
  # Example: k6 run --env API_BASE_URL=$API_BASE_URL scripts/tests/load-tests.js
  echo "[load-tests] TODO: implement real staging load tests"
else
  echo "[load-tests] Testing against local docker-compose stack"
  # TODO: implement local load tests
  # Example: k6 run scripts/tests/load-tests.js
  echo "[load-tests] TODO: implement real local load tests"
fi