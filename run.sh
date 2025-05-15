#!/usr/bin/env bash

set -eou pipefail

# Build the container
podman build -t mayer-monitor .

# Run the container with environment variables from .env
podman run --env-file .env mayer-monitor
