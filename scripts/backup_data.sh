#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/docker/docker-compose.yml}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backups}"
DB_SERVICE="${DB_SERVICE:-db}"
TS="${TS:-$(date +%Y%m%d_%H%M%S)}"

mkdir -p "${BACKUP_DIR}"

DB_BACKUP="${BACKUP_DIR}/db_${TS}.dump"
MEDIA_BACKUP="${BACKUP_DIR}/media_${TS}.tar.gz"
MANIFEST="${BACKUP_DIR}/backup_${TS}.manifest"

hash_file() {
  local file_path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${file_path}" | awk '{print $1}'
  else
    shasum -a 256 "${file_path}" | awk '{print $1}'
  fi
}

echo ">> Generando backup de BD en ${DB_BACKUP}"
docker compose -f "${COMPOSE_FILE}" exec -T "${DB_SERVICE}" sh -lc \
  'export PGPASSWORD="${POSTGRES_PASSWORD}"; pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc' \
  > "${DB_BACKUP}"

echo ">> Generando backup de media en ${MEDIA_BACKUP}"
tar -czf "${MEDIA_BACKUP}" -C "${ROOT_DIR}" media

DB_HASH="$(hash_file "${DB_BACKUP}")"
MEDIA_HASH="$(hash_file "${MEDIA_BACKUP}")"
MEDIA_FILE_COUNT="$(find "${ROOT_DIR}/media" -type f | wc -l | tr -d ' ')"

{
  echo "timestamp=${TS}"
  echo "db_backup=${DB_BACKUP}"
  echo "db_sha256=${DB_HASH}"
  echo "media_backup=${MEDIA_BACKUP}"
  echo "media_sha256=${MEDIA_HASH}"
  echo "media_file_count=${MEDIA_FILE_COUNT}"
} > "${MANIFEST}"

echo ">> Backup completado"
echo "   - DB: ${DB_BACKUP}"
echo "   - MEDIA: ${MEDIA_BACKUP}"
echo "   - MANIFEST: ${MANIFEST}"
