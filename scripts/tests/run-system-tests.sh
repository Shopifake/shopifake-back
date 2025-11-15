#!/usr/bin/env bash

# System/E2E tests script that supports two modes:
# - local: tests against docker-compose stack (default)
# - staging: tests against deployed staging environment

set -euo pipefail

echo "[system-tests] Starting system/E2E test suite in $ENV mode..."

# Define all services routed through the gateway
# Gateway routes: /api/{service-name}/**
SERVICES=(
  "access"
  "audit"
  "catalog"
  "customers"
  "inventory"
  "orders"
  "pricing"
  "sales-dashboard"
  "sites"
)

check_health() {
  local service_name=$1
  local url=$2
  
  echo -n "[health-check] Testing $service_name ... "
  
  if curl -sf "$url" > /dev/null 2>&1; then
    echo "✓ UP"
    return 0
  else
    echo "✗ DOWN"
    return 1
  fi
}

if [[ "$ENV" == "staging" ]]; then
  echo "[system-tests] Testing against staging at: $API_BASE_URL"
  BASE_URL="$API_BASE_URL"
else
  echo "[system-tests] Testing against local docker-compose stack"
  BASE_URL="http://gateway:8080"
fi

echo "[system-tests] Gateway base URL: $BASE_URL"
echo ""

FAILED_SERVICES=()

# Test gateway itself first
if ! check_health "gateway" "$BASE_URL/actuator/health"; then
  echo "[system-tests] ✗ Gateway is down, cannot proceed with service checks"
  exit 1
fi

# Test all services through the gateway
for service_name in "${SERVICES[@]}"; do
  health_url="$BASE_URL/api/$service_name/actuator/health"
  
  if ! check_health "$service_name" "$health_url"; then
    FAILED_SERVICES+=("$service_name")
  fi
done

echo ""
if [ ${#FAILED_SERVICES[@]} -eq 0 ]; then
  echo "[system-tests] ✓ All services are healthy"
  exit 0
else
  echo "[system-tests] ✗ Failed services: ${FAILED_SERVICES[*]}"
  exit 1
fi

