#!/usr/bin/env bash
set -euo pipefail
umask 077

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd -P)"
BACKUP_ROOT="${BACKUP_DIR:-$HOME/Backups/document-ai-rpa}"
MONGODB_CONTAINER="${MONGODB_CONTAINER:-document-ai-rpa-mongodb}"
MONGODB_DATABASE="${MONGODB_DATABASE:-document_ai_rpa}"
API_PORT="${API_PORT:-8000}"
RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-7}"
DOCUMENTS_DIR="$PROJECT_ROOT/backend/storage/documents"
MARKER_NAME=".managed-by-document-ai-rpa-backup"
MARKER_VALUE="document-ai-rpa-backup-v1"

if [[ ! "$RETENTION_COUNT" =~ ^[1-9][0-9]*$ ]]; then
  printf 'BACKUP_RETENTION_COUNT must be a positive integer.\n' >&2
  exit 1
fi

mkdir -p "$BACKUP_ROOT"
BACKUP_ROOT="$(cd "$BACKUP_ROOT" && pwd -P)"
case "$BACKUP_ROOT/" in
  "$PROJECT_ROOT/"*)
    printf 'Backup destination must be outside the project repository.\n' >&2
    exit 1
    ;;
esac

if [[ ! -d "$DOCUMENTS_DIR" ]]; then
  printf 'Document storage directory not found: %s\n' "$DOCUMENTS_DIR" >&2
  exit 1
fi

if ! command -v lsof > /dev/null || ! command -v pgrep > /dev/null; then
  printf 'lsof and pgrep are required to check that writers are stopped.\n' >&2
  exit 1
fi
if lsof -nP -iTCP:"$API_PORT" -sTCP:LISTEN -t > /dev/null 2>&1; then
  printf 'Stop the backend listening on port %s before backing up.\n' "$API_PORT" >&2
  exit 1
fi
if pgrep -f '[p]ython_rpa_processor.py' > /dev/null 2>&1; then
  printf 'Stop the RPA worker before backing up.\n' >&2
  exit 1
fi

if [[ "$(docker inspect --format '{{.State.Running}}' "$MONGODB_CONTAINER" 2>/dev/null || true)" != "true" ]]; then
  printf 'MongoDB container is not running: %s\n' "$MONGODB_CONTAINER" >&2
  exit 1
fi

if ! docker exec "$MONGODB_CONTAINER" mongosh --quiet "$MONGODB_DATABASE" \
  --eval 'quit(db.runCommand({ping: 1}).ok ? 0 : 1)' > /dev/null 2>&1; then
  printf 'MongoDB is not responding in container %s.\n' "$MONGODB_CONTAINER" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FINAL_DIR="$BACKUP_ROOT/$STAMP"
if [[ -e "$FINAL_DIR" ]]; then
  printf 'Backup already exists for timestamp %s. Retry in a second.\n' "$STAMP" >&2
  exit 1
fi
STAGING_DIR="$(mktemp -d "$BACKUP_ROOT/.in-progress-$STAMP.XXXXXX")"

cleanup() {
  if [[ -n "${STAGING_DIR:-}" && -d "$STAGING_DIR" ]]; then
    case "$STAGING_DIR" in
      "$BACKUP_ROOT"/.in-progress-*) rm -rf "$STAGING_DIR" ;;
    esac
  fi
}
trap cleanup EXIT

printf 'Backing up MongoDB database %s...\n' "$MONGODB_DATABASE"
docker exec "$MONGODB_CONTAINER" mongodump \
  --db "$MONGODB_DATABASE" --archive --gzip \
  > "$STAGING_DIR/mongodb.archive.gz"
test -s "$STAGING_DIR/mongodb.archive.gz"

printf 'Archiving uploaded and processed documents...\n'
tar -czf "$STAGING_DIR/documents.tar.gz" \
  -C "$PROJECT_ROOT/backend/storage" documents
test -s "$STAGING_DIR/documents.tar.gz"
tar -tzf "$STAGING_DIR/documents.tar.gz" > /dev/null

(
  cd "$STAGING_DIR"
  shasum -a 256 mongodb.archive.gz documents.tar.gz > SHA256SUMS
  shasum -a 256 -c SHA256SUMS
)
printf '%s\n' "$MARKER_VALUE" > "$STAGING_DIR/$MARKER_NAME"
mv "$STAGING_DIR" "$FINAL_DIR"
STAGING_DIR=""

prune_old_backups() {
  local candidate name marker count=0
  while IFS= read -r candidate; do
    [[ -d "$candidate" ]] || continue
    name="${candidate##*/}"
    [[ "$name" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] || continue
    marker="$candidate/$MARKER_NAME"
    [[ -f "$marker" ]] || continue
    [[ "$(cat "$marker")" == "$MARKER_VALUE" ]] || continue
    count=$((count + 1))
    if (( count > RETENTION_COUNT )); then
      case "$candidate/" in
        "$BACKUP_ROOT/"*) ;;
        *)
          printf 'Refusing to prune outside backup directory: %s\n' "$candidate" >&2
          return 1
          ;;
      esac
      printf 'Removing expired managed backup: %s\n' "$candidate"
      rm -rf "$candidate"
    fi
  done < <(for candidate in "$BACKUP_ROOT"/[0-9]*; do printf '%s\n' "$candidate"; done | sort -r)
}

prune_old_backups
printf 'Verified backup created at: %s\n' "$FINAL_DIR"
printf 'Contents: mongodb.archive.gz, documents.tar.gz, SHA256SUMS\n'
