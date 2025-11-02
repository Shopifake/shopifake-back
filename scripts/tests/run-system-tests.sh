#!/usr/bin/env bash

# System/E2E tests script that supports two modes:
# - local: tests against docker-compose stack (default)
# - staging: tests against deployed staging environment

set -euo pipefail

ENV="${ENV}"
API_BASE_URL="${API_BASE_URL}"

echo "[system-tests] Starting system/E2E test suite in $ENV mode..."

if [[ "$ENV" == "staging" ]]; then
  echo "[system-tests] Testing against staging at: $API_BASE_URL"
  # TODO: implement staging system tests
  # Example: k6 run --env API_BASE_URL=$API_BASE_URL tests/system/*.js
  echo "[system-tests] TODO: implement real staging system tests"
else
  echo "[system-tests] Testing against local docker-compose stack"
  # TODO: implement local system tests
  # Example: k6 run tests/system/*.js
  echo "[system-tests] TODO: implement real local system tests"
fi

