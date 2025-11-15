# Test runner image for system/E2E tests
FROM alpine:3.19

# Install required tools for tests
RUN apk add --no-cache \
    bash \
    curl \
    jq

# Copy test scripts directory
COPY scripts/tests/ /tests/
RUN chmod +x /tests/*.sh

WORKDIR /tests

# Default to staging mode
ENV ENV=staging

ENTRYPOINT ["/tests/run-system-tests.sh"]

