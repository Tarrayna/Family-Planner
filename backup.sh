#!/usr/bin/env bash
# Nightly, polled by a systemd timer on the deploy server (see README.md).
# Takes a consistent SQLite backup — sqlite3's online backup API, safe to run
# against the live WAL-mode database; a raw `cp` could copy a torn snapshot —
# plus a tarball of the photos volume, and ships both to the NAS mount.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# Point this at wherever the NAS share is mounted on this VM (NFS/SMB).
NAS_DIR="${NAS_BACKUP_DIR:-/mnt/nas/planner-backups}"
KEEP_DAYS=14
STAMP="$(date +%F)"

mkdir -p "$NAS_DIR"

docker compose exec -T api python -c "
import sqlite3
src = sqlite3.connect('/app/data/planner.db')
dst = sqlite3.connect('/tmp/backup.db')
src.backup(dst)
dst.close()
src.close()
"
docker compose cp api:/tmp/backup.db "$NAS_DIR/planner-$STAMP.db"
docker compose exec -T api rm -f /tmp/backup.db

docker compose exec -T api tar -C /app/photos -czf - . > "$NAS_DIR/photos-$STAMP.tar.gz"

sqlite3 "$NAS_DIR/planner-$STAMP.db" "PRAGMA integrity_check" | grep -qx ok \
  || { echo "$(date -Is): backup integrity check FAILED for $STAMP" >&2; exit 1; }

find "$NAS_DIR" -name 'planner-*.db' -mtime "+$KEEP_DAYS" -delete
find "$NAS_DIR" -name 'photos-*.tar.gz' -mtime "+$KEEP_DAYS" -delete

echo "$(date -Is): backup complete ($STAMP)"
