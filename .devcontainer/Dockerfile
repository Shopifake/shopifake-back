FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Core tooling (git, curl, etc.) + Node.js 20 for scripts.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        wget \
        jq \
        git \
        unzip \
        gnupg; \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash; \
    apt-get install -y --no-install-recommends nodejs; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

