#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

PROJECT_DIR="${PROJECT_DIR:-/root/my-flask-project}"
DATA_DIR="${DATA_DIR:-$PROJECT_DIR/data}"
BACKUP_ROOT="${BACKUP_ROOT:-/root/backups/my-flask-project}"
BYPY="${BYPY:-/root/backups/tools/bypy-venv/bin/bypy}"
REMOTE_DIR="${REMOTE_DIR:-my-flask-project/data-backups}"
REMOTE_RETENTION="${REMOTE_RETENTION:-14}"
PART_SIZE="${PART_SIZE:-16M}"

TMP_ROOT="$BACKUP_ROOT/tmp"
LOG_DIR="$BACKUP_ROOT/logs"
LOCK_FILE="$BACKUP_ROOT/baidu-backup.lock"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
WORK_DIR="$TMP_ROOT/work-$TIMESTAMP"
ARCHIVE_NAME="my-flask-project-data-$TIMESTAMP.tar.gz"
ARCHIVE_PATH="$TMP_ROOT/$ARCHIVE_NAME"
SHA_PATH="$ARCHIVE_PATH.sha256"
MANIFEST_PATH="$ARCHIVE_PATH.manifest.txt"
LOG_PATH="$LOG_DIR/baidu-backup-$TIMESTAMP.log"

mkdir -p "$TMP_ROOT" "$LOG_DIR"
exec > >(tee -a "$LOG_PATH") 2>&1

cleanup() {
  rm -rf "$WORK_DIR"
  rm -f "$ARCHIVE_PATH" "$SHA_PATH" "$MANIFEST_PATH" "$ARCHIVE_PATH".part-*
  find "$TMP_ROOT" -mindepth 1 -maxdepth 1 -mtime +1 -exec rm -rf {} +
}
trap cleanup EXIT

echo "[$(date -Iseconds)] Baidu backup started"

if [ ! -d "$DATA_DIR" ]; then
  echo "Data directory does not exist: $DATA_DIR" >&2
  exit 1
fi

if [ ! -x "$BYPY" ]; then
  echo "bypy executable does not exist: $BYPY" >&2
  exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "Another Baidu backup is already running; exiting."
  exit 0
fi

mkdir -p "$WORK_DIR/data"

echo "Copying non-database data files..."
tar -C "$DATA_DIR" \
  --exclude='./main.db' \
  --exclude='./upload_staging/tmp' \
  --exclude='./upload_staging/locks' \
  -cf - . | tar -C "$WORK_DIR/data" -xf -

if [ -f "$DATA_DIR/main.db" ]; then
  echo "Creating consistent SQLite backup for main.db..."
  python3 - "$DATA_DIR/main.db" "$WORK_DIR/data/main.db" <<'PY'
import os
import sqlite3
import sys

source_path, backup_path = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(backup_path), exist_ok=True)

source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True, timeout=60)
try:
    target = sqlite3.connect(backup_path)
    try:
        source.backup(target)
        result = target.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError(f"SQLite integrity_check failed: {result}")
    finally:
        target.close()
finally:
    source.close()
PY
fi

{
  echo "created_utc=$TIMESTAMP"
  echo "hostname=$(hostname)"
  echo "project_dir=$PROJECT_DIR"
  echo "data_dir=$DATA_DIR"
  echo "remote_dir=/apps/bypy/$REMOTE_DIR"
  if git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "git_head=$(git -C "$PROJECT_DIR" rev-parse HEAD 2>/dev/null || true)"
    echo "git_status_short_begin"
    git -C "$PROJECT_DIR" status --short 2>/dev/null || true
    echo "git_status_short_end"
  fi
  echo "data_size_begin"
  du -h --max-depth=2 "$DATA_DIR" 2>/dev/null || true
  echo "data_size_end"
} > "$WORK_DIR/backup_metadata.txt"

echo "Creating archive $ARCHIVE_PATH..."
tar -C "$WORK_DIR" -czf "$ARCHIVE_PATH" data backup_metadata.txt
sha256sum "$ARCHIVE_PATH" > "$SHA_PATH"

echo "Archive size:"
du -h "$ARCHIVE_PATH" "$SHA_PATH"

echo "Splitting archive into $PART_SIZE parts for more reliable Baidu uploads..."
split -b "$PART_SIZE" -d -a 3 "$ARCHIVE_PATH" "$ARCHIVE_PATH.part-"

{
  echo "archive_name=$ARCHIVE_NAME"
  echo "archive_sha256=$(awk '{ print $1 }' "$SHA_PATH")"
  echo "part_size=$PART_SIZE"
  echo "restore_hint=cat ${ARCHIVE_NAME}.part-* > ${ARCHIVE_NAME} && sha256sum -c ${ARCHIVE_NAME}.sha256"
  echo "parts_begin"
  sha256sum "$ARCHIVE_PATH".part-*
  echo "parts_end"
} > "$MANIFEST_PATH"

remote_file_size() {
  local remote_name="$1"
  "$BYPY" list "$REMOTE_DIR" |
    awk -v name="$remote_name" '$1 == "F" && $2 == name { print $3; exit }'
}

upload_and_verify() {
  local local_path="$1"
  local remote_name="$2"
  local expected_size actual_size

  expected_size="$(stat -c '%s' "$local_path")"
  "$BYPY" upload "$local_path" "$REMOTE_DIR/$remote_name"
  actual_size="$(remote_file_size "$remote_name")"

  if [ "$actual_size" != "$expected_size" ]; then
    echo "Remote verification failed for $remote_name: expected $expected_size bytes, got ${actual_size:-missing}" >&2
    return 1
  fi
}

echo "Ensuring remote directory exists: /apps/bypy/$REMOTE_DIR"
"$BYPY" mkdir my-flask-project >/dev/null 2>&1 || true
"$BYPY" mkdir "$REMOTE_DIR" >/dev/null 2>&1 || true

echo "Uploading archive to Baidu Netdisk..."
for part_path in "$ARCHIVE_PATH".part-*; do
  upload_and_verify "$part_path" "$(basename "$part_path")"
done
upload_and_verify "$SHA_PATH" "$(basename "$SHA_PATH")"
upload_and_verify "$MANIFEST_PATH" "$(basename "$MANIFEST_PATH")"

echo "Applying remote retention: keep latest $REMOTE_RETENTION archives"
mapfile -t OLD_ARCHIVES < <(
  "$BYPY" list "$REMOTE_DIR" |
    awk '$1 == "F" && $2 ~ /^my-flask-project-data-[0-9]{8}_[0-9]{6}\.tar\.gz\.manifest\.txt$/ { sub(/\.manifest\.txt$/, "", $2); print $2 }' |
    sort -r |
    tail -n +"$((REMOTE_RETENTION + 1))"
)

for old_archive in "${OLD_ARCHIVES[@]}"; do
  [ -n "$old_archive" ] || continue
  echo "Deleting old remote archive set: $old_archive"
  mapfile -t old_files < <(
    "$BYPY" list "$REMOTE_DIR" |
      awk -v prefix="$old_archive" '$1 == "F" && index($2, prefix) == 1 { print $2 }'
  )
  for old_file in "${old_files[@]}"; do
    "$BYPY" delete "$REMOTE_DIR/$old_file" || true
  done
done

echo "Remote backup list:"
"$BYPY" list "$REMOTE_DIR"

echo "[$(date -Iseconds)] Baidu backup completed: $ARCHIVE_NAME"
