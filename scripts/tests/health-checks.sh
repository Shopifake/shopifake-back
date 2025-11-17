#!/usr/bin/env bash

# Health check utilities for system tests
# Tests all application services through their health endpoints

set -euo pipefail

# Color output for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check a single service health endpoint
# Args: $1 = service name, $2 = health URL
check_service_health() {
  local service_name=$1
  local url=$2

  echo -n "[health-check] Testing $service_name ... "

  # Capture curl output and HTTP status code
  local http_code
  local curl_output
  curl_output=$(curl -sf -w "\n%{http_code}" "$url" 2>&1)
  local curl_exit=$?

  if [ $curl_exit -eq 0 ]; then
    # Extract HTTP status code (last line)
    http_code=$(echo "$curl_output" | tail -n1)
    # Extract response body (all lines except last)
    local response_body=$(echo "$curl_output" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
      echo -e "${GREEN}✓ UP${NC} (HTTP $http_code)"
      return 0
    else
      echo -e "${RED}✗ DOWN${NC} (HTTP $http_code)"
      echo "    URL: $url"
      if [ -n "$response_body" ]; then
        echo "    Response: $response_body"
      fi
      return 1
    fi
  else
    # curl failed (connection error, DNS error, etc.)
    echo -e "${RED}✗ DOWN${NC}"
    echo "    URL: $url"
    echo "    Error: Failed to connect or invalid response"
    if [ -n "$curl_output" ]; then
      echo "    Details: $(echo "$curl_output" | head -n1)"
    fi
    return 1
  fi
}

# Run health checks for all application services
# Args: $1 = base URL (e.g., http://gateway:8080 or https://staging-api.example.com)
run_all_health_checks() {
  local base_url=$1
  local failed_services=()

  echo ""
  echo "=========================================="
  echo "  System Health Checks"
  echo "=========================================="
  echo "Base URL: $base_url"
  echo ""

  # Check gateway itself first
  echo "--- Gateway ---"
  if ! check_service_health "gateway" "$base_url/actuator/health"; then
    echo ""
    echo -e "${RED}[ERROR] Gateway is down, cannot proceed with service checks${NC}"
    return 1
  fi

  # Spring Boot services (routed through gateway at /api/{service}/actuator/health)
  echo ""
  echo "--- Spring Boot Services ---"
  local spring_services=(
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

  for service in "${spring_services[@]}"; do
    local health_url="$base_url/api/$service/actuator/health"
    if ! check_service_health "$service" "$health_url"; then
      failed_services+=("$service")
    fi
  done

  # FastAPI/Python services (routed through gateway at /api/{service}/health)
  echo ""
  echo "--- Python Services ---"
  local python_services=(
    "chatbot"
    "recommender"
  )

  for service in "${python_services[@]}"; do
    local health_url="$base_url/api/$service/health"
    if ! check_service_health "$service" "$health_url"; then
      failed_services+=("$service")
    fi
  done

  # Auth services (Node.js/custom health endpoints)
  # Note: These services use /healthz endpoint, not /health
  # They may not be routed through gateway, so check if gateway routes exist first
  echo ""
  echo "--- Auth Services ---"
  local auth_services=(
    "auth-b2c"
    "auth-b2e"
  )

  for service in "${auth_services[@]}"; do
    # Auth services use /healthz endpoint (if routed through gateway)
    local health_url="$base_url/api/$service/healthz"
    if ! check_service_health "$service" "$health_url"; then
      failed_services+=("$service")
    fi
  done

  # Summary
  echo ""
  echo "=========================================="
  if [ ${#failed_services[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All services are healthy${NC}"
    echo "=========================================="
    return 0
  else
    echo -e "${RED}✗ Failed services: ${failed_services[*]}${NC}"
    echo "=========================================="
    return 1
  fi
}

