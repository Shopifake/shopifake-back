#!/usr/bin/env bash

# System/E2E tests orchestrator
# Supports two modes:
# - local: tests against docker-compose stack (default)
# - staging: tests against deployed staging environment

set -euo pipefail

# Get script directory to source helper files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source health check utilities
source "$SCRIPT_DIR/health-checks.sh"

# Determine test environment
ENV="${ENV:-local}"

echo ""
echo "=========================================="
echo "  Shopifake System Tests"
echo "=========================================="
echo "Environment: $ENV"
echo ""

# Determine base URL based on environment
if [[ "$ENV" == "staging" ]]; then
  if [[ -z "${API_BASE_URL:-}" ]]; then
    echo "[ERROR] API_BASE_URL must be set for staging tests"
    exit 1
  fi
  BASE_URL="$API_BASE_URL"
  echo "Target: $BASE_URL (deployed staging)"
else
  # In local mode, use localhost since tests run on the host (CI runner) and gateway port is mapped
  BASE_URL="http://localhost:8080"
  echo "Target: $BASE_URL (local docker-compose via port mapping)"
fi

# Run health checks for all services
run_all_health_checks "$BASE_URL"

