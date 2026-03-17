#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

INPUT_PATH=""
TARGET_FILE=""
YES=0

usage() {
  cat <<'EOF'
Uso:
  scripts/backups/restore_env.sh [ruta_respaldo|ruta_env] [--target-file RUTA] [--yes]

Notas:
  - Si no se pasa ruta, usa backups/latest.
  - Si el archivo destino existe, exige --yes.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-file)
      TARGET_FILE="${2:-}"
      shift 2
      ;;
    --yes)
      YES=1
      shift
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

ENV_FILE=""

if [[ -n "${INPUT_PATH}" && -f "${INPUT_PATH}" ]]; then
  ENV_FILE="${INPUT_PATH}"
else
  RUN_DIR="$(resolve_run_dir "${INPUT_PATH}")"
  MANIFEST_FILE="${RUN_DIR}/manifest.env"
  ENV_FILE="$(manifest_get "env_backup" || true)"
  if [[ -z "${ENV_FILE}" || ! -f "${ENV_FILE}" ]]; then
    ENV_FILE="$(resolve_artifact_in_run_dir "${RUN_DIR}" '*_env_*.secure.env')"
  fi
  if [[ -z "${ENV_FILE}" || ! -f "${ENV_FILE}" ]]; then
    ENV_FILE="$(resolve_artifact_in_run_dir "${RUN_DIR}" '*_env_example_*.env.example')"
  fi
fi

[[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]] || die "No se encontró respaldo de entorno."

if [[ -z "${TARGET_FILE}" ]]; then
  TARGET_FILE="${ROOT_DIR}/.env.restored"
fi

if [[ "${TARGET_FILE}" != /* ]]; then
  TARGET_FILE="${ROOT_DIR}/${TARGET_FILE}"
fi

if [[ -e "${TARGET_FILE}" ]]; then
  [[ "${YES}" -eq 1 ]] || die "El archivo destino ${TARGET_FILE} ya existe. Usa --yes."
fi

mkdir -p "$(dirname "${TARGET_FILE}")"
cp "${ENV_FILE}" "${TARGET_FILE}"
chmod 600 "${TARGET_FILE}" 2>/dev/null || true

log "Entorno restaurado."
log "Destino: ${TARGET_FILE}"
