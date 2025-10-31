FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Install development CLIs required by Shopifake services.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl wget jq git unzip \
       rabbitmq-server \
    && rm -rf /var/lib/apt/lists/*

# Install Auth0 CLI.
RUN curl -fsSL https://cli.auth0.com/install.sh | bash

# Install Node.js 20 for tooling scripts.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

