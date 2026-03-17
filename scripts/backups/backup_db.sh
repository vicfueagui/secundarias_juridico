#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Uso:
  scripts/backups/backup_db.sh [--mode docker|direct|auto]

Opciones:
  --mode   Fuerza el camino de respaldo de PostgreSQL.
           - docker: usa docker compose exec sobre el servicio db
           - direct: usa pg_dump directo con POSTGRES_*
           - auto: detecta automáticamente (default)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      DB_BACKUP_MODE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Opción no reconocida: $1"
      ;;
  esac
done

require_pg_tool pg_dump PG_DUMP_BIN
require_pg_tool pg_restore PG_RESTORE_BIN
init_backup_context

DB_MODE="$(detect_db_mode)"
DUMP_FILE="${BACKUP_RUN_DIR}/${PROJECT_SLUG}_${ENV_SLUG}_db_${TIMESTAMP}.dump"

set_manifest "db_mode" "${DB_MODE}"
set_manifest "db_backup" "${DUMP_FILE}"
set_manifest "db_name" "${POSTGRES_DB}"

case "${DB_MODE}" in
  docker)
    require_cmd docker
    COMPOSE_FILE_RESOLVED="$(resolve_compose_file_or_die)"
    ensure_compose_service_running "${COMPOSE_FILE_RESOLVED}" "${DB_SERVICE}"
    log "Generando dump de PostgreSQL por Docker en ${DUMP_FILE}"
    docker compose -f "${COMPOSE_FILE_RESOLVED}" exec -T "${DB_SERVICE}" sh -lc \
      'export PGPASSWORD="${POSTGRES_PASSWORD}"; pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --format=custom --no-owner --no-privileges' \
      > "${DUMP_FILE}"
    set_manifest "db_source" "docker:${DB_SERVICE}"
    set_manifest "db_compose_file" "${COMPOSE_FILE_RESOLVED}"
    ;;
  direct)
    PG_DUMP_BIN_PATH="$(resolve_pg_tool pg_dump PG_DUMP_BIN)"
    direct_db_ready || die "No hay respuesta en ${POSTGRES_HOST}:${POSTGRES_PORT} para PostgreSQL directo."
    log "Generando dump de PostgreSQL directo en ${DUMP_FILE}"
    PGPASSWORD="${POSTGRES_PASSWORD}" \
      "${PG_DUMP_BIN_PATH}" -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
      --format=custom --no-owner --no-privileges > "${DUMP_FILE}"
    set_manifest "db_source" "direct:${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
    ;;
esac

"$(resolve_pg_tool pg_restore PG_RESTORE_BIN)" --list "${DUMP_FILE}" >/dev/null

DB_HASH="$(set_checksum_entry "${DUMP_FILE}")"
SOURCE_TABLES="$(db_query_value "${DB_MODE}" "${POSTGRES_DB}" "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" || true)"
SOURCE_MIGRATIONS="$(db_query_value "${DB_MODE}" "${POSTGRES_DB}" "SELECT count(*) FROM django_migrations;" || true)"

set_manifest "db_sha256" "${DB_HASH}"
set_manifest "db_size_bytes" "$(file_size_bytes "${DUMP_FILE}")"
set_manifest "db_tables_source" "${SOURCE_TABLES:-desconocido}"
set_manifest "db_migrations_source" "${SOURCE_MIGRATIONS:-desconocido}"

log "Respaldo DB listo."
log "Archivo: ${DUMP_FILE}"
log "SHA256: ${DB_HASH}"
