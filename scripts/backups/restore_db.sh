#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

INPUT_PATH=""
TARGET_DB=""
DROP_EXISTING=0
YES=0

usage() {
  cat <<'EOF'
Uso:
  scripts/backups/restore_db.sh [ruta_respaldo|ruta_dump] [--target-db NOMBRE] [--drop-existing] [--yes] [--mode docker|direct|auto]

Notas:
  - Si no se pasa ruta, intenta usar backups/latest.
  - Por seguridad, NO restaura sobre la base configurada si no se usa --drop-existing --yes.
  - Si no se indica --target-db, crea una base nueva con sufijo _restore_YYYYMMDD.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-db)
      TARGET_DB="${2:-}"
      shift 2
      ;;
    --drop-existing)
      DROP_EXISTING=1
      shift
      ;;
    --yes)
      YES=1
      shift
      ;;
    --mode)
      DB_BACKUP_MODE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -z "${INPUT_PATH}" ]]; then
        INPUT_PATH="$1"
        shift
      else
        die "Argumento no reconocido: $1"
      fi
      ;;
  esac
done

load_env
require_pg_tool pg_restore PG_RESTORE_BIN

DB_MODE="$(detect_db_mode)"
if [[ "${DB_MODE}" == "docker" ]]; then
  require_cmd docker
  COMPOSE_FILE_RESOLVED="$(resolve_compose_file_or_die)"
  ensure_compose_service_running "${COMPOSE_FILE_RESOLVED}" "${DB_SERVICE}"
else
  direct_db_ready || die "No hay conexión PostgreSQL directa disponible."
fi

if [[ -n "${INPUT_PATH}" && -f "${INPUT_PATH}" ]]; then
  DUMP_FILE="${INPUT_PATH}"
else
  RUN_DIR="$(resolve_run_dir "${INPUT_PATH}")"
  MANIFEST_FILE="${RUN_DIR}/manifest.env"
  DUMP_FILE="$(manifest_get "db_backup" || true)"
  [[ -n "${DUMP_FILE}" && -f "${DUMP_FILE}" ]] || DUMP_FILE="$(resolve_artifact_in_run_dir "${RUN_DIR}" '*_db_*.dump')"
fi

[[ -n "${DUMP_FILE}" && -f "${DUMP_FILE}" ]] || die "No se encontró dump de base de datos."

if [[ -z "${TARGET_DB}" ]]; then
  TARGET_DB="${POSTGRES_DB}_restore_$(date +%Y%m%d)"
fi

ensure_safe_db_name "${TARGET_DB}"

if [[ "${TARGET_DB}" == "${POSTGRES_DB}" ]]; then
  [[ "${DROP_EXISTING}" -eq 1 && "${YES}" -eq 1 ]] || die "Restaurar sobre la base activa requiere --drop-existing --yes."
fi

if database_exists "${DB_MODE}" "${TARGET_DB}"; then
  [[ "${DROP_EXISTING}" -eq 1 ]] || die "La base ${TARGET_DB} ya existe. Usa --drop-existing."
  [[ "${YES}" -eq 1 ]] || die "Eliminar una base existente requiere --yes."
  log "Eliminando base existente ${TARGET_DB}"
  drop_database "${DB_MODE}" "${TARGET_DB}"
fi

log "Creando base ${TARGET_DB}"
create_database "${DB_MODE}" "${TARGET_DB}"

log "Restaurando dump ${DUMP_FILE} en ${TARGET_DB}"
restore_dump_to_db "${DB_MODE}" "${DUMP_FILE}" "${TARGET_DB}"

RESTORED_TABLES="$(db_query_value "${DB_MODE}" "${TARGET_DB}" "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" || true)"
RESTORED_MIGRATIONS="$(db_query_value "${DB_MODE}" "${TARGET_DB}" "SELECT count(*) FROM django_migrations;" || true)"

log "Restauración DB completada."
log "Base destino: ${TARGET_DB}"
log "Tablas públicas: ${RESTORED_TABLES:-desconocido}"
log "django_migrations: ${RESTORED_MIGRATIONS:-desconocido}"
