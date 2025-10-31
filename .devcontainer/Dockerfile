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

# GitHub Actions runner (act) to test workflows locally.
ARG ACT_VERSION=v0.2.82
RUN set -eux; \
    ARCH="$(uname -m)"; \
    case "${ARCH}" in \
        x86_64) ACT_ARCH=Linux_x86_64 ;; \
        aarch64|arm64) ACT_ARCH=Linux_arm64 ;; \
        *) echo "Unsupported architecture: ${ARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/nektos/act/releases/download/${ACT_VERSION}/act_${ACT_ARCH}.tar.gz" -o /tmp/act.tar.gz; \
    tar -xzf /tmp/act.tar.gz -C /usr/local/bin act; \
    rm /tmp/act.tar.gz

WORKDIR /workspace

