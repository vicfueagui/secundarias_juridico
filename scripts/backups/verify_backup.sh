#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

RUN_INPUT="${1:-}"
TIMESTAMP="${TIMESTAMP:-$(timestamp_now)}"
load_env
RUN_DIR="$(resolve_run_dir "${RUN_INPUT}")"
MANIFEST_FILE="${RUN_DIR}/manifest.env"
CHECKSUM_FILE="${RUN_DIR}/checksums.sha256"
REPORT_FILE="${RUN_DIR}/backup_verification_${TIMESTAMP}.md"

DUMP_FILE=""
MEDIA_ARCHIVE=""
MEDIA_NOTE=""
CODE_ARCHIVE=""
GIT_BUNDLE=""
ENV_FILE=""
ENV_REDACTED=""

DB_STATUS="SKIPPED"
MEDIA_STATUS="SKIPPED"
CODE_STATUS="SKIPPED"
CHECKSUM_STATUS="SKIPPED"
ENV_STATUS="SKIPPED"
OVERALL_STATUS="OK"

CHECKSUM_NOTES=""
DB_NOTES=""
MEDIA_NOTES=""
CODE_NOTES=""
ENV_NOTES=""

TEST_DB=""
MEDIA_TMP_DIR=""

cleanup() {
  if [[ -n "${TEST_DB}" && -n "${DB_MODE:-}" ]]; then
    drop_database "${DB_MODE}" "${TEST_DB}" >/dev/null 2>&1 || true
  fi

  if [[ -n "${MEDIA_TMP_DIR}" && -d "${MEDIA_TMP_DIR}" ]]; then
    rm -rf "${MEDIA_TMP_DIR}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ -f "${MANIFEST_FILE}" ]]; then
  DUMP_FILE="$(manifest_get "db_backup" || true)"
  MEDIA_ARCHIVE="$(manifest_get "media_backup" || true)"
  MEDIA_NOTE="$(manifest_get "media_note" || true)"
  CODE_ARCHIVE="$(manifest_get "code_backup" || true)"
  GIT_BUNDLE="$(manifest_get "git_bundle" || true)"
  ENV_FILE="$(manifest_get "env_backup" || true)"
  ENV_REDACTED="$(manifest_get "env_redacted" || true)"
fi

[[ -n "${DUMP_FILE}" && -f "${DUMP_FILE}" ]] || DUMP_FILE="$(resolve_artifact_in_run_dir "${RUN_DIR}" '*_db_*.dump')"
[[ -n "${MEDIA_ARCHIVE}" && -f "${MEDIA_ARCHIVE}" ]] || MEDIA_ARCHIVE="$(resolve_artifact_in_run_dir "${RUN_DIR}" '*_media_*.tar.gz')"
[[ -n "${MEDIA_NOTE}" && -f "${MEDIA_NOTE}" ]] || MEDIA_NOTE="$(resolve_artifact_in_run_dir "${RUN_DIR}" 'media_backup_skipped.txt')"
[[ -n "${CODE_ARCHIVE}" && -f "${CODE_ARCHIVE}" ]] || CODE_ARCHIVE="$(resolve_artifact_in_run_dir "${RUN_DIR}" '*_code_*.tar.gz')"
[[ -n "${GIT_BUNDLE}" && -f "${GIT_BUNDLE}" ]] || GIT_BUNDLE="$(resolve_artifact_in_run_dir "${RUN_DIR}" '*_git_*.bundle')"
[[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]] || ENV_FILE="$(resolve_artifact_in_run_dir "${RUN_DIR}" '*_env_*.secure.env')"
[[ -n "${ENV_REDACTED}" && -f "${ENV_REDACTED}" ]] || ENV_REDACTED="$(resolve_artifact_in_run_dir "${RUN_DIR}" 'env_redacted_*.env')"

if [[ -f "${CHECKSUM_FILE}" ]]; then
  CHECKSUM_STATUS="OK"
  while IFS= read -r line; do
    [[ -n "${line}" ]] || continue
    EXPECTED_HASH="${line%% *}"
    FILE_NAME="${line##* }"
    ARTIFACT_PATH="${RUN_DIR}/${FILE_NAME}"
    if [[ ! -f "${ARTIFACT_PATH}" ]]; then
      CHECKSUM_STATUS="FAIL"
      CHECKSUM_NOTES+="- Falta el archivo listado en checksums: ${FILE_NAME}"$'\n'
      OVERALL_STATUS="FAIL"
      continue
    fi
    ACTUAL_HASH="$(sha256_of_file "${ARTIFACT_PATH}")"
    if [[ "${ACTUAL_HASH}" != "${EXPECTED_HASH}" ]]; then
      CHECKSUM_STATUS="FAIL"
      CHECKSUM_NOTES+="- SHA256 distinto para ${FILE_NAME}"$'\n'
      OVERALL_STATUS="FAIL"
    fi
  done < "${CHECKSUM_FILE}"
  [[ -n "${CHECKSUM_NOTES}" ]] || CHECKSUM_NOTES="- Checksums validados correctamente."$'\n'
else
  CHECKSUM_STATUS="WARN"
  CHECKSUM_NOTES="- No existe checksums.sha256 en este respaldo."$'\n'
  [[ "${OVERALL_STATUS}" == "FAIL" ]] || OVERALL_STATUS="WARN"
fi

if [[ -n "${DUMP_FILE}" && -f "${DUMP_FILE}" ]]; then
  require_pg_tool pg_restore PG_RESTORE_BIN
  DB_MODE="$(manifest_get "db_mode" || true)"
  [[ -n "${DB_MODE}" ]] || DB_MODE="$(detect_db_mode)"

  if [[ "${DB_MODE}" == "docker" ]]; then
    COMPOSE_FILE_RESOLVED="$(manifest_get "db_compose_file" || true)"
    [[ -n "${COMPOSE_FILE_RESOLVED}" ]] || COMPOSE_FILE_RESOLVED="$(resolve_compose_file_or_die)"
    ensure_compose_service_running "${COMPOSE_FILE_RESOLVED}" "${DB_SERVICE}"
  fi

  "$(resolve_pg_tool pg_restore PG_RESTORE_BIN)" --list "${DUMP_FILE}" >/dev/null

  TEST_DB="restore_check_${TIMESTAMP//[^0-9]/}"
  TEST_DB="${TEST_DB:0:40}"
  ensure_safe_db_name "${TEST_DB}"

  if database_exists "${DB_MODE}" "${TEST_DB}"; then
    drop_database "${DB_MODE}" "${TEST_DB}"
  fi

  SOURCE_TABLES="$(db_query_value "${DB_MODE}" "${POSTGRES_DB}" "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" || true)"
  SOURCE_MIGRATIONS="$(db_query_value "${DB_MODE}" "${POSTGRES_DB}" "SELECT count(*) FROM django_migrations;" || true)"

  create_database "${DB_MODE}" "${TEST_DB}"
  restore_dump_to_db "${DB_MODE}" "${DUMP_FILE}" "${TEST_DB}"

  RESTORED_TABLES="$(db_query_value "${DB_MODE}" "${TEST_DB}" "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" || true)"
  RESTORED_MIGRATIONS="$(db_query_value "${DB_MODE}" "${TEST_DB}" "SELECT count(*) FROM django_migrations;" || true)"

  if [[ "${SOURCE_TABLES}" == "${RESTORED_TABLES}" && "${SOURCE_MIGRATIONS}" == "${RESTORED_MIGRATIONS}" ]]; then
    DB_STATUS="OK"
    DB_NOTES+="- Dump legible con pg_restore --list."$'\n'
    DB_NOTES+="- Restauración temporal exitosa en ${TEST_DB}."$'\n'
    DB_NOTES+="- Tablas origen/restauradas: ${SOURCE_TABLES}/${RESTORED_TABLES}."$'\n'
    DB_NOTES+="- django_migrations origen/restauradas: ${SOURCE_MIGRATIONS}/${RESTORED_MIGRATIONS}."$'\n'
  else
    DB_STATUS="FAIL"
    DB_NOTES+="- La restauración temporal no coincide con la base origen."$'\n'
    DB_NOTES+="- Tablas origen/restauradas: ${SOURCE_TABLES}/${RESTORED_TABLES}."$'\n'
    DB_NOTES+="- django_migrations origen/restauradas: ${SOURCE_MIGRATIONS}/${RESTORED_MIGRATIONS}."$'\n'
    OVERALL_STATUS="FAIL"
  fi
else
  DB_STATUS="FAIL"
  DB_NOTES="- No se encontró dump de base de datos en el respaldo."$'\n'
  OVERALL_STATUS="FAIL"
fi

if [[ -n "${MEDIA_ARCHIVE}" && -f "${MEDIA_ARCHIVE}" ]]; then
  LC_ALL=C tar -tzf "${MEDIA_ARCHIVE}" >/dev/null
  MEDIA_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/project_secu_juridi_media_verify.XXXXXX")"
  LC_ALL=C tar -xzf "${MEDIA_ARCHIVE}" -C "${MEDIA_TMP_DIR}"

  RESTORED_MEDIA_FILES="$(find "${MEDIA_TMP_DIR}" -type f | wc -l | tr -d ' ')"
  MEDIA_SOURCE_MODE="$(manifest_get "media_mode" || true)"
  SOURCE_MEDIA_FILES=""

  case "${MEDIA_SOURCE_MODE}" in
    docker)
      COMPOSE_FILE_RESOLVED="$(manifest_get "media_compose_file" || true)"
      [[ -n "${COMPOSE_FILE_RESOLVED}" ]] || COMPOSE_FILE_RESOLVED="$(resolve_compose_file_or_die)"
      if compose_service_running "${COMPOSE_FILE_RESOLVED}" "${WEB_SERVICE}"; then
        SOURCE_MEDIA_FILES="$(docker compose -f "${COMPOSE_FILE_RESOLVED}" exec -T "${WEB_SERVICE}" sh -lc 'find /app/media -type f | wc -l' | tr -d ' \r')"
      fi
      ;;
    host)
      if MEDIA_SOURCE_DIR="$(resolve_host_media_dir 2>/dev/null)"; then
        SOURCE_MEDIA_FILES="$(find "${MEDIA_SOURCE_DIR}" -type f | wc -l | tr -d ' ')"
      fi
      ;;
  esac

  if [[ -n "${SOURCE_MEDIA_FILES}" ]]; then
    if [[ "${SOURCE_MEDIA_FILES}" == "${RESTORED_MEDIA_FILES}" ]]; then
      MEDIA_STATUS="OK"
      MEDIA_NOTES+="- Archive extraíble correctamente."$'\n'
      MEDIA_NOTES+="- Archivos origen/restaurados: ${SOURCE_MEDIA_FILES}/${RESTORED_MEDIA_FILES}."$'\n'
    else
      MEDIA_STATUS="FAIL"
      MEDIA_NOTES+="- Conteo distinto entre origen y restauración temporal."$'\n'
      MEDIA_NOTES+="- Archivos origen/restaurados: ${SOURCE_MEDIA_FILES}/${RESTORED_MEDIA_FILES}."$'\n'
      OVERALL_STATUS="FAIL"
    fi
  else
    MEDIA_STATUS="WARN"
    MEDIA_NOTES+="- Archive extraíble correctamente."$'\n'
    MEDIA_NOTES+="- No se pudo comparar contra origen vivo en este entorno."$'\n'
    [[ "${OVERALL_STATUS}" == "FAIL" ]] || OVERALL_STATUS="WARN"
  fi
elif [[ -n "${MEDIA_NOTE}" && -f "${MEDIA_NOTE}" ]]; then
  MEDIA_STATUS="SKIPPED"
  MEDIA_NOTES="- Este respaldo documentó que no había media aplicable para respaldar."$'\n'
else
  MEDIA_STATUS="WARN"
  MEDIA_NOTES="- No se encontró archive de media ni nota de omisión."$'\n'
  [[ "${OVERALL_STATUS}" == "FAIL" ]] || OVERALL_STATUS="WARN"
fi

if [[ -n "${CODE_ARCHIVE}" && -f "${CODE_ARCHIVE}" ]]; then
  LC_ALL=C tar -tzf "${CODE_ARCHIVE}" >/dev/null
  if LC_ALL=C tar -tzf "${CODE_ARCHIVE}" | grep -Eq '(^|/)manage\.py$'; then
    CODE_STATUS="OK"
    CODE_NOTES+="- Archive del código legible y con manage.py presente."$'\n'
  else
    CODE_STATUS="FAIL"
    CODE_NOTES+="- El archive del código no contiene manage.py."$'\n'
    OVERALL_STATUS="FAIL"
  fi

  if [[ -n "${GIT_BUNDLE}" && -f "${GIT_BUNDLE}" ]]; then
    if git -C "${ROOT_DIR}" bundle verify "${GIT_BUNDLE}" >/dev/null 2>&1; then
      CODE_NOTES+="- Git bundle verificado correctamente."$'\n'
    else
      CODE_STATUS="FAIL"
      CODE_NOTES+="- El git bundle no pasó verificación."$'\n'
      OVERALL_STATUS="FAIL"
    fi
  else
    CODE_NOTES+="- No hay git bundle; el respaldo de código principal sigue siendo el tar.gz."$'\n'
  fi
else
  CODE_STATUS="FAIL"
  CODE_NOTES="- No se encontró archive de código."$'\n'
  OVERALL_STATUS="FAIL"
fi

if [[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]]; then
  if grep -Eq '^[A-Za-z_][A-Za-z0-9_]*=' "${ENV_FILE}"; then
    ENV_STATUS="OK"
    ENV_NOTES+="- Respaldo de entorno encontrado."$'\n'
  else
    ENV_STATUS="FAIL"
    ENV_NOTES+="- El respaldo de entorno no tiene formato esperado KEY=VALUE."$'\n'
    OVERALL_STATUS="FAIL"
  fi
  if [[ -n "${ENV_REDACTED}" && -f "${ENV_REDACTED}" ]]; then
    ENV_NOTES+="- Archivo redactado disponible para auditoría de llaves."$'\n'
  fi
else
  ENV_STATUS="WARN"
  ENV_NOTES="- No se encontró respaldo de entorno."$'\n'
  [[ "${OVERALL_STATUS}" == "FAIL" ]] || OVERALL_STATUS="WARN"
fi

{
  printf '# Verificación de respaldo\n\n'
  printf -- '- Fecha de verificación: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')"
  printf -- '- Respaldo inspeccionado: %s\n' "${RUN_DIR}"
  printf -- '- Resultado general: %s\n' "${OVERALL_STATUS}"
  printf '\n## Checksums\n'
  printf -- '- Estado: %s\n' "${CHECKSUM_STATUS}"
  printf '%s' "${CHECKSUM_NOTES}"
  printf '\n## Base de datos\n'
  printf -- '- Estado: %s\n' "${DB_STATUS}"
  printf '%s' "${DB_NOTES}"
  printf '\n## Media\n'
  printf -- '- Estado: %s\n' "${MEDIA_STATUS}"
  printf '%s' "${MEDIA_NOTES}"
  printf '\n## Código fuente\n'
  printf -- '- Estado: %s\n' "${CODE_STATUS}"
  printf '%s' "${CODE_NOTES}"
  printf '\n## Entorno\n'
  printf -- '- Estado: %s\n' "${ENV_STATUS}"
  printf '%s' "${ENV_NOTES}"
} > "${REPORT_FILE}"

if [[ -f "${MANIFEST_FILE}" ]]; then
  set_manifest "verify_report" "${REPORT_FILE}"
  set_manifest "verify_status" "${OVERALL_STATUS}"
fi

log "Reporte de verificación: ${REPORT_FILE}"

if [[ "${OVERALL_STATUS}" == "FAIL" ]]; then
  exit 1
fi
