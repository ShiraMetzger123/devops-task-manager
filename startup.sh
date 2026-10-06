#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/ubuntu/devops-task-manager"

log() {
    echo "[$(date -Is)] $*"
}

log "Starting DevOps Task Manager boot startup"

log "Changing into project directory: ${PROJECT_DIR}"
cd "${PROJECT_DIR}"

if [ ! -f .env ]; then
    log "ERROR: .env file not found in ${PROJECT_DIR}; refusing to start" >&2
    exit 1
fi
log ".env file present (contents not read or displayed)"

log "Fetching latest main from origin"
git fetch origin main

log "Updating working tree to origin/main (fast-forward only)"
git merge --ff-only origin/main

log "Starting application with docker compose up -d"
docker compose up -d

log "Current docker compose service status:"
docker compose ps

log "Startup complete"
