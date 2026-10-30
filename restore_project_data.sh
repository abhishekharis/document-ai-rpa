#!/usr/bin/env bash
# Restore a backup made by backup_project_data.sh.
#
# Usage: restore_project_data.sh <backup-dir> [--force]
#
# By default restores into a scratch database ($TARGET_DATABASE, default
# "<MONGODB_DATABASE>_restore") and a scratch documents directory
# ($TARGET_DOCUMENTS_DIR, default "<backup-dir>/restored-documents"), so a
# restore never touches live data. Set TARGET_DATABASE=$MONGODB_DATABASE and
# TARGET_DOCUMENTS_DIR=backend/storage/documents together with --force to
# overwrite live data (stop the backend and RPA worker first).
set -euo pipefail
umask 077

BACKUP_DIR="${1:-}"
FORCE="${2:-}"
MONGODB_CONTAINER="${MONGODB_CONTAINER:-document-ai-rpa-mongodb}"
MONGODB_DATABASE="${MONGODB_DATABASE:-document_ai_rpa}"
TARGET_DATABASE="${TARGET_DATABASE:-${MONGODB_DATABASE}_restore}"

if [[ -z "$BACKUP_DIR" || ! -d "$BACKUP_DIR" ]]; then
  printf 'Usage: %s <backup-dir> [--force]\n' "$0" >&2
  exit 1
fi
BACKUP_DIR="$(cd "$BACKUP_DIR" && pwd -P)"
TARGET_DOCUMENTS_DIR="${TARGET_DOCUMENTS_DIR:-$BACKUP_DIR/restored-documents}"

if [[ ! -f "$BACKUP_DIR/.managed-by-document-ai-rpa-backup" ]]; then
  printf 'Not a managed backup directory: %s\n' "$BACKUP_DIR" >&2
  exit 1
fi

(cd "$BACKUP_DIR" && shasum -a 256 -c SHA256SUMS)

if [[ "$(docker inspect --format '{{.State.Running}}' "$MONGODB_CONTAINER" 2>/dev/null || true)" != "true" ]]; then
  printf 'MongoDB container is not running: %s\n' "$MONGODB_CONTAINER" >&2
  exit 1
fi

existing="$(docker exec "$MONGODB_CONTAINER" mongosh --quiet "$TARGET_DATABASE" \
  --eval 'print(db.getCollectionNames().length)')"
if [[ "$existing" != "0" && "$FORCE" != "--force" ]]; then
  printf 'Database %s already has %s collections. Re-run with --force to overwrite.\n' \
    "$TARGET_DATABASE" "$existing" >&2
  exit 1
fi
if [[ -e "$TARGET_DOCUMENTS_DIR" && -n "$(ls -A "$TARGET_DOCUMENTS_DIR" 2>/dev/null)" && "$FORCE" != "--force" ]]; then
  printf 'Documents directory %s is not empty. Re-run with --force to overwrite.\n' \
    "$TARGET_DOCUMENTS_DIR" >&2
  exit 1
fi

printf 'Restoring MongoDB into database %s...\n' "$TARGET_DATABASE"
DROP_FLAG=""
[[ "$FORCE" == "--force" ]] && DROP_FLAG="--drop"
docker exec -i "$MONGODB_CONTAINER" mongorestore --archive --gzip $DROP_FLAG \
  --nsFrom "${MONGODB_DATABASE}.*" --nsTo "${TARGET_DATABASE}.*" \
  < "$BACKUP_DIR/mongodb.archive.gz"

printf 'Extracting documents into %s...\n' "$TARGET_DOCUMENTS_DIR"
mkdir -p "$TARGET_DOCUMENTS_DIR"
tar -xzf "$BACKUP_DIR/documents.tar.gz" -C "$TARGET_DOCUMENTS_DIR" --strip-components=1

printf 'Restore complete.\n'
