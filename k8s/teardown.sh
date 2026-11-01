#!/usr/bin/env bash
# Delete the local cluster and everything in it (the Docker Compose setup is not affected).
set -euo pipefail
kind delete cluster --name "${CLUSTER:-dataguard}"
