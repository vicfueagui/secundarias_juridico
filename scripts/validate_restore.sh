#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/docker/docker-compose.yml}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backups}"
TS="${TS:-$(date +%Y%m%d_%H%M%S)}"

DUMP_FILE="${1:-}"
MEDIA_ARCHIVE="${2:-}"

if [[ -z "${DUMP_FILE}" ]]; then
  DUMP_FILE="$(ls -1t "${BACKUP_DIR}"/db_*.dump 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "${MEDIA_ARCHIVE}" ]]; then
  MEDIA_ARCHIVE="$(ls -1t "${BACKUP_DIR}"/media_*.tar.gz 2>/dev/null | head -n 1 || true)"
fi

if [[ -z "${DUMP_FILE}" || ! -f "${DUMP_FILE}" ]]; then
  echo "Error: no se encontró dump de base de datos para validar restore."
  exit 1
fi
if [[ -z "${MEDIA_ARCHIVE}" || ! -f "${MEDIA_ARCHIVE}" ]]; then
  echo "Error: no se encontró backup de media para validar restore."
  exit 1
fi

TEST_DB="restore_test_${TS}"
RESTORE_MEDIA_DIR="${BACKUP_DIR}/restore_media_${TS}"
REPORT_FILE="${BACKUP_DIR}/restore_validation_${TS}.md"

cleanup() {
  rm -rf "${RESTORE_MEDIA_DIR}" >/dev/null 2>&1 || true
  docker compose -f "${COMPOSE_FILE}" exec -T postgres sh -lc \
    "export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"; dropdb -U \"\${POSTGRES_USER}\" --if-exists \"${TEST_DB}\"" \
    >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo ">> Iniciando validación de restore"
echo "   - dump: ${DUMP_FILE}"
echo "   - media: ${MEDIA_ARCHIVE}"
echo "   - test_db: ${TEST_DB}"

SOURCE_DB_TABLES="$(
  docker compose -f "${COMPOSE_FILE}" exec -T postgres sh -lc \
    'export PGPASSWORD="${POSTGRES_PASSWORD}"; psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='\''public'\'';"' \
    | tr -d ' \r'
)"

SOURCE_DB_MIGRATIONS="$(
  docker compose -f "${COMPOSE_FILE}" exec -T postgres sh -lc \
    'export PGPASSWORD="${POSTGRES_PASSWORD}"; psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "SELECT count(*) FROM django_migrations;"' \
    | tr -d ' \r'
)"

echo ">> Creando base de prueba ${TEST_DB}"
docker compose -f "${COMPOSE_FILE}" exec -T postgres sh -lc \
  "export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"; createdb -U \"\${POSTGRES_USER}\" \"${TEST_DB}\""

echo ">> Restaurando dump en base de prueba"
docker compose -f "${COMPOSE_FILE}" exec -T postgres sh -lc \
  "export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"; pg_restore -U \"\${POSTGRES_USER}\" -d \"${TEST_DB}\" --no-owner --no-privileges" \
  < "${DUMP_FILE}"

RESTORED_DB_TABLES="$(
  docker compose -f "${COMPOSE_FILE}" exec -T postgres sh -lc \
    "export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"; psql -U \"\${POSTGRES_USER}\" -d \"${TEST_DB}\" -tAc \"SELECT count(*) FROM information_schema.tables WHERE table_schema='public';\"" \
    | tr -d ' \r'
)"

RESTORED_DB_MIGRATIONS="$(
  docker compose -f "${COMPOSE_FILE}" exec -T postgres sh -lc \
    "export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"; psql -U \"\${POSTGRES_USER}\" -d \"${TEST_DB}\" -tAc \"SELECT count(*) FROM django_migrations;\"" \
    | tr -d ' \r'
)"

echo ">> Validando archive de media"
mkdir -p "${RESTORE_MEDIA_DIR}"
tar -xzf "${MEDIA_ARCHIVE}" -C "${RESTORE_MEDIA_DIR}"

ORIGINAL_MEDIA_FILES="$(find "${ROOT_DIR}/media" -type f | wc -l | tr -d ' ')"
RESTORED_MEDIA_FILES="$(find "${RESTORE_MEDIA_DIR}/media" -type f | wc -l | tr -d ' ')"

DB_OK=0
MEDIA_OK=0

if [[ "${RESTORED_DB_TABLES}" == "${SOURCE_DB_TABLES}" && "${RESTORED_DB_MIGRATIONS}" == "${SOURCE_DB_MIGRATIONS}" ]]; then
  DB_OK=1
fi

if [[ "${RESTORED_MEDIA_FILES}" == "${ORIGINAL_MEDIA_FILES}" ]]; then
  MEDIA_OK=1
fi

{
  echo "# Validación de Restore"
  echo ""
  echo "- Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "- Dump: ${DUMP_FILE}"
  echo "- Media archive: ${MEDIA_ARCHIVE}"
  echo "- Base temporal: ${TEST_DB}"
  echo ""
  echo "## Resultados DB"
  echo "- Tablas origen: ${SOURCE_DB_TABLES}"
  echo "- Tablas restauradas: ${RESTORED_DB_TABLES}"
  echo "- django_migrations origen: ${SOURCE_DB_MIGRATIONS}"
  echo "- django_migrations restauradas: ${RESTORED_DB_MIGRATIONS}"
  echo "- Estado DB: $([[ ${DB_OK} -eq 1 ]] && echo 'OK' || echo 'FAIL')"
  echo ""
  echo "## Resultados Media"
  echo "- Archivos media origen: ${ORIGINAL_MEDIA_FILES}"
  echo "- Archivos media restaurados: ${RESTORED_MEDIA_FILES}"
  echo "- Estado Media: $([[ ${MEDIA_OK} -eq 1 ]] && echo 'OK' || echo 'FAIL')"
  echo ""
  echo "## Veredicto"
  if [[ ${DB_OK} -eq 1 && ${MEDIA_OK} -eq 1 ]]; then
    echo "- RESULTADO: VALIDADO"
  else
    echo "- RESULTADO: INVALIDO"
  fi
} > "${REPORT_FILE}"

echo ">> Reporte: ${REPORT_FILE}"

if [[ ${DB_OK} -ne 1 || ${MEDIA_OK} -ne 1 ]]; then
  echo "Error: la validación de restore no pasó."
  exit 1
fi

echo ">> Validación de restore completada y exitosa."
