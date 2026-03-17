#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

MODE="auto"

usage() {
  cat <<'EOF'
Uso:
  scripts/backups/backup_env.sh [--mode auto|current|example|none]

Opciones:
  --mode
    auto: usa .env si existe; si no, .env.example
    current: exige .env
    example: usa .env.example
    none: no genera respaldo de entorno
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
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

init_backup_context

ENV_SOURCE=""
ENV_FILE=""
ENV_BACKUP=""
ENV_REDACTED=""

case "${MODE}" in
  auto)
    if [[ -f "${ROOT_DIR}/.env" ]]; then
      ENV_SOURCE="current"
      ENV_FILE="${ROOT_DIR}/.env"
      ENV_BACKUP="${BACKUP_RUN_DIR}/${PROJECT_SLUG}_${ENV_SLUG}_env_${TIMESTAMP}.secure.env"
    elif [[ -f "${ROOT_DIR}/.env.example" ]]; then
      ENV_SOURCE="example"
      ENV_FILE="${ROOT_DIR}/.env.example"
      ENV_BACKUP="${BACKUP_RUN_DIR}/${PROJECT_SLUG}_${ENV_SLUG}_env_example_${TIMESTAMP}.env.example"
    else
      MODE="none"
    fi
    ;;
  current)
    [[ -f "${ROOT_DIR}/.env" ]] || die "No existe .env para respaldar."
    ENV_SOURCE="current"
    ENV_FILE="${ROOT_DIR}/.env"
    ENV_BACKUP="${BACKUP_RUN_DIR}/${PROJECT_SLUG}_${ENV_SLUG}_env_${TIMESTAMP}.secure.env"
    ;;
  example)
    [[ -f "${ROOT_DIR}/.env.example" ]] || die "No existe .env.example para respaldar."
    ENV_SOURCE="example"
    ENV_FILE="${ROOT_DIR}/.env.example"
    ENV_BACKUP="${BACKUP_RUN_DIR}/${PROJECT_SLUG}_${ENV_SLUG}_env_example_${TIMESTAMP}.env.example"
    ;;
  none)
    ;;
  *)
    die "Modo de entorno no reconocido: ${MODE}"
    ;;
esac

set_manifest "env_mode" "${MODE}"

if [[ "${MODE}" == "none" ]]; then
  set_manifest "env_note" "No se generó respaldo de entorno."
  log "No se generó respaldo de entorno."
  exit 0
fi

cp "${ENV_FILE}" "${ENV_BACKUP}"
if [[ "${ENV_SOURCE}" == "current" ]]; then
  chmod 600 "${ENV_BACKUP}"
fi

ENV_REDACTED="${BACKUP_RUN_DIR}/env_redacted_${TIMESTAMP}.env"
awk -F= '
  /^[[:space:]]*#/ || /^[[:space:]]*$/ { print; next }
  /^[^=]+=/ {
    key=$1
    value=substr($0, index($0, "=") + 1)
    status=(length(value) > 0 ? "<set>" : "<empty>")
    print key "=" status
    next
  }
  { print }
' "${ENV_FILE}" > "${ENV_REDACTED}"

ENV_HASH="$(set_checksum_entry "${ENV_BACKUP}")"
ENV_REDACTED_HASH="$(set_checksum_entry "${ENV_REDACTED}")"

set_manifest "env_source" "${ENV_SOURCE}"
set_manifest "env_backup" "${ENV_BACKUP}"
set_manifest "env_sha256" "${ENV_HASH}"
set_manifest "env_redacted" "${ENV_REDACTED}"
set_manifest "env_redacted_sha256" "${ENV_REDACTED_HASH}"

log "Respaldo de entorno listo."
log "Archivo: ${ENV_BACKUP}"
