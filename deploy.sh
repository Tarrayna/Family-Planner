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
# containers whose image or config changed in docker-compose.yml itself.
docker compose build
docker compose up -d

# Caddyfile is bind-mounted, not baked into an image or referenced by
# docker-compose.yml's own config — `up -d` has no way to notice its
# *contents* changed, so proxy never restarts on its own after a
# Caddyfile-only edit. Restart it explicitly whenever this deploy touched it.
if git diff --name-only "$local_rev" "$remote_rev" | grep -qx Caddyfile; then
  docker compose restart proxy
fi

echo "$(date -Is): deploy complete ($remote_rev)"
