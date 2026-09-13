#!/usr/bin/env bash
# Polled by a systemd timer (see README.md) on the deploy server. Checks
# origin/main for new commits and, if there are any, fast-forwards and
# rebuilds/restarts. Fast-forward only (never resets/discards) — if the
# server's checkout ever diverges from origin/main, this fails loudly
# instead of silently throwing away whatever's there.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

git fetch origin main

local_rev=$(git rev-parse HEAD)
remote_rev=$(git rev-parse origin/main)

if [ "$local_rev" = "$remote_rev" ]; then
  exit 0
fi

echo "$(date -Is): deploying $remote_rev (was $local_rev)"
git merge --ff-only origin/main

# Only rebuilds the api image if its Dockerfile/requirements/app code
# actually changed (Docker layer caching); `up -d` only recreates
# containers whose image or config changed, so db/proxy stay untouched
# unless the Caddyfile or docker-compose.yml did.
docker compose build
docker compose up -d

echo "$(date -Is): deploy complete ($remote_rev)"
