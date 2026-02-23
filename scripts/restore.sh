#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/docker-compose.yml}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backups}"
DB_SERVICE="${DB_SERVICE:-db}"
WEB_SERVICE="${WEB_SERVICE:-web}"

DUMP_FILE=""
MEDIA_ARCHIVE=""

usage() {
  cat <<'EOF'
Uso:
  scripts/restore.sh --dump <archivo.dump> --media <archivo.tar.gz>

Opciones:
  --dump    Ruta al dump de PostgreSQL (formato custom pg_dump -Fc)
  --media   Ruta al respaldo media (.tar.gz)

Si no se envían opciones, toma automáticamente los más recientes de ./backups.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dump)
      DUMP_FILE="${2:-}"
      shift 2
      ;;
    --media)
      MEDIA_ARCHIVE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: opción no reconocida: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${DUMP_FILE}" ]]; then
  DUMP_FILE="$(ls -1t "${BACKUP_DIR}"/db_*.dump 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "${MEDIA_ARCHIVE}" ]]; then
  MEDIA_ARCHIVE="$(ls -1t "${BACKUP_DIR}"/media_*.tar.gz 2>/dev/null | head -n 1 || true)"
fi

if [[ -z "${DUMP_FILE}" || ! -f "${DUMP_FILE}" ]]; then
  echo "Error: dump no encontrado: ${DUMP_FILE:-<vacío>}" >&2
  exit 1
fi
if [[ -z "${MEDIA_ARCHIVE}" || ! -f "${MEDIA_ARCHIVE}" ]]; then
  echo "Error: backup media no encontrado: ${MEDIA_ARCHIVE:-<vacío>}" >&2
  exit 1
fi

ensure_running() {
  local service="$1"
  if ! docker compose -f "${COMPOSE_FILE}" ps --status running --services | grep -qx "${service}"; then
    echo "Error: el servicio '${service}' debe estar corriendo para restaurar." >&2
    exit 1
  fi
}

ensure_running "${DB_SERVICE}"
ensure_running "${WEB_SERVICE}"

echo ">> Restaurando base de datos desde ${DUMP_FILE}"
docker compose -f "${COMPOSE_FILE}" exec -T "${DB_SERVICE}" sh -lc \
  'export PGPASSWORD="${POSTGRES_PASSWORD}"; dropdb -U "${POSTGRES_USER}" --if-exists "${POSTGRES_DB}"; createdb -U "${POSTGRES_USER}" "${POSTGRES_DB}"'

docker compose -f "${COMPOSE_FILE}" exec -T "${DB_SERVICE}" sh -lc \
  'export PGPASSWORD="${POSTGRES_PASSWORD}"; pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner --no-privileges' \
  < "${DUMP_FILE}"

echo ">> Restaurando media desde ${MEDIA_ARCHIVE}"
docker compose -f "${COMPOSE_FILE}" exec -T "${WEB_SERVICE}" sh -lc 'rm -rf /app/media/* && mkdir -p /app/media'
docker compose -f "${COMPOSE_FILE}" exec -T "${WEB_SERVICE}" sh -lc 'cd /app && tar -xzf -' < "${MEDIA_ARCHIVE}"

echo ">> Restore completado"
echo "   - DB restaurada desde: ${DUMP_FILE}"
echo "   - MEDIA restaurada desde: ${MEDIA_ARCHIVE}"
