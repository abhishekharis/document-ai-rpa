# Investigation: MongoDB stopped on a WiredTiger checksum error

**Severity:** ⭐⭐⭐⭐ High — the database stopped and required repair before the API could start.

## Problem

The MongoDB container exited with code 133. Its logs reported a checksum mismatch in a WiredTiger data block, so MongoDB stopped rather than opening the damaged data. The backend could not connect. After `mongod --repair` completed successfully, the health check passed and 7 invoice records were present.

## Root cause

WiredTiger detected that a block in its on-disk data did not match its recorded checksum. This confirms database-file corruption, but not what caused it. The available evidence did not establish whether the initiating event was an abrupt shutdown, Docker storage issue, or something else.

## Data safety and recovery

MongoDB holds invoice records and audit logs. Original uploads and processed page images are stored separately under `backend/storage/documents/`; a MongoDB dump alone does not back up those files.

Do not remove or recreate the Docker volume when MongoDB fails to start. Stop the backend and RPA worker, preserve the data volume before any repair attempt, and work on a copy. Treat `mongod --repair` as a recovery measure, not a substitute for a backup: it may discard damaged data.

### Routine backup

Run from the project root after stopping the backend and RPA worker; the script refuses to run while it detects either writer. MongoDB stays running. The script creates a timestamped folder under `~/Backups/document-ai-rpa/` containing the MongoDB dump, document archive, and SHA-256 manifest. It validates the checksums and document archive before retaining the backup, then keeps the seven newest folders it created. It only prunes folders with its own timestamp format and ownership marker.

```bash
bash ./backup_project_data.sh
```

To verify a specific backup, use its timestamped folder:

```bash
cd "$HOME/Backups/document-ai-rpa/<timestamp>"
shasum -a 256 -c SHA256SUMS
tar -tzf documents.tar.gz > /dev/null
```

Set `BACKUP_DIR` to use another destination or `BACKUP_RETENTION_COUNT` to change the limit. The default location is on this laptop, and the archives contain invoice data; use an encrypted disk or FileVault and keep an encrypted copy off the laptop for protection against device loss. File permissions are restricted, but the script does not encrypt archives itself.

### Restore drill

Test the database archive in a temporary MongoDB container with no connection to the project volume. The container is automatically removed on stop; the `--drop` applies only to its disposable restore-check database. In a new terminal, set `backup_dir` and `stamp` to the values used when creating the backup.

```bash
set -euo pipefail
drill_name="document-ai-rpa-restore-drill-$stamp"
docker run --rm -d --name "$drill_name" mongo:7.0 --bind_ip_all > /dev/null
cleanup() { docker stop "$drill_name" > /dev/null 2>&1 || true; }
trap cleanup EXIT
ready=0
for attempt in $(seq 1 30); do
  if docker exec "$drill_name" mongosh --quiet \
    --eval 'quit(db.runCommand({ping: 1}).ok ? 0 : 1)' > /dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
test "$ready" = 1
docker exec -i "$drill_name" mongorestore \
  --nsFrom='document_ai_rpa.*' \
  --nsTo='document_ai_rpa_restore_check.*' \
  --drop --archive --gzip \
  < "$backup_dir/mongodb-$stamp.archive.gz"
for database in document_ai_rpa document_ai_rpa_restore_check; do
  docker exec "$drill_name" mongosh --quiet "$database" \
    --eval 'printjson({invoices: db.invoices.countDocuments(), audit_logs: db.audit_logs.countDocuments()})'
done
```

Compare both counts between the source and restored database. Also extract the document archive into a new, empty temporary directory and confirm that each restored invoice has its original under `documents/<document_id>/original/`. Do not extract over the live storage directory as part of a drill.

### If MongoDB will not start

1. Stop the backend and RPA worker, then stop MongoDB with `docker compose stop mongodb`. Do not repeatedly restart it or delete its volume.
2. Make a read-only archive of the stopped data volume before attempting repair. This command discovers the Compose-created volume name and writes the archive outside the repository:

   ```bash
   set -euo pipefail
   umask 077
   backup_dir="$HOME/Backups/document-ai-rpa"
   stamp="$(date -u +%Y%m%dT%H%M%SZ)"
   mkdir -p "$backup_dir"
   backup_dir="$(cd "$backup_dir" && pwd)"
   volume="$(docker inspect document-ai-rpa-mongodb \
     --format '{{range .Mounts}}{{if eq .Destination "/data/db"}}{{.Name}}{{end}}{{end}}')"
   test -n "$volume"
   docker run --rm \
     -v "$volume:/backupdata:ro" \
     -v "$backup_dir:/backup" \
     mongo:7.0 tar -czf "/backup/mongodb-volume-$stamp.tar.gz" \
       -C /backupdata .
   (
     cd "$backup_dir"
     shasum -a 256 "mongodb-volume-$stamp.tar.gz" \
       > "SHA256SUMS-volume-$stamp"
   )
   ```
3. Preserve the original volume archive. To make a separate recovery copy, restore it into a new named volume and run repair against only that copy. Continue in the same terminal, or set `backup_dir` and `stamp` to the values from step 2:

   ```bash
   (cd "$backup_dir" && shasum -a 256 -c "SHA256SUMS-volume-$stamp")
   recovery_volume="document-ai-rpa-mongodb-recovery-$stamp"
   recovery_name="document-ai-rpa-recovery-$stamp"
   docker volume create "$recovery_volume"
   docker run --rm \
     -v "$recovery_volume:/backupdata" \
     -v "$backup_dir:/backup:ro" \
     mongo:7.0 tar -xzf "/backup/mongodb-volume-$stamp.tar.gz" \
       -C /backupdata
   docker run --rm \
     -v "$recovery_volume:/data/db" \
     mongo:7.0 mongod --repair --dbpath /data/db
   docker run --rm -d --name "$recovery_name" \
     -v "$recovery_volume:/data/db" \
     mongo:7.0 --bind_ip_all
   docker exec "$recovery_name" mongosh --quiet document_ai_rpa \
     --eval 'printjson({invoices: db.invoices.countDocuments(), audit_logs: db.audit_logs.countDocuments()})'
   docker stop "$recovery_name"
   ```

   Keep the original volume untouched. Validate counts and invoice originals on the recovery copy before making any decision about using it. Do not point the normal Compose service at the recovery volume as part of this drill.
4. Once MongoDB starts, take a normal logical dump and document-file backup, then perform the restore drill and verify invoice records against their stored originals.

### Restore a normal backup to the project database

This is a destructive recovery step, not a drill. Stop the backend and RPA worker, preserve the current database and file storage first, verify the selected backup checksums, and confirm that replacing the backed-up collections is intended. Keep MongoDB running, then restore:

```bash
docker exec -i document-ai-rpa-mongodb mongorestore \
  --drop --archive --gzip \
  < "$backup_dir/mongodb-$stamp.archive.gz"
```

`--drop` replaces collections present in the archive. Restore the document archive separately into a new, restricted staging directory, confirm it contains `documents/<document_id>/original/`, and only then restore those files after preserving the current `backend/storage/documents/` directory. Restart the backend and RPA worker after records and files have been checked together.

## Verification

The logical dump/restore drill and offline volume-copy/repair sequence were exercised using disposable MongoDB containers or volumes with synthetic invoice and audit records. Each restored copy returned matching counts (2 invoices and 1 audit record). The raw-volume drill used a healthy copy; it verified the archive, copy, repair command, and read-back flow, not recovery from injected corruption. The project database and its persistent volume were not used.

## Takeaway

A successful database repair proves MongoDB can open the repaired files; it does not identify the corruption's cause or replace a tested backup. Back up both MongoDB and the separate document files, and preserve the original volume before recovery attempts.
