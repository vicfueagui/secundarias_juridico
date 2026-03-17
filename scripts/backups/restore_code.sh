#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

INPUT_PATH=""
TARGET_DIR=""
YES=0

usage() {
  cat <<'EOF'
Uso:
  scripts/backups/restore_code.sh [ruta_respaldo|ruta_code.tar.gz] [--target-dir RUTA] [--yes]

Notas:
  - Si no se pasa ruta, usa backups/latest.
  - Si la carpeta destino ya contiene archivos, exige --yes.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-dir)
      TARGET_DIR="${2:-}"
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

if [[ -n "${INPUT_PATH}" && -f "${INPUT_PATH}" ]]; then
  CODE_ARCHIVE="${INPUT_PATH}"
else
  RUN_DIR="$(resolve_run_dir "${INPUT_PATH}")"
  MANIFEST_FILE="${RUN_DIR}/manifest.env"
  CODE_ARCHIVE="$(manifest_get "code_backup" || true)"
  [[ -n "${CODE_ARCHIVE}" && -f "${CODE_ARCHIVE}" ]] || CODE_ARCHIVE="$(resolve_artifact_in_run_dir "${RUN_DIR}" '*_code_*.tar.gz')"
fi

[[ -n "${CODE_ARCHIVE}" && -f "${CODE_ARCHIVE}" ]] || die "No se encontró respaldo de código."
LC_ALL=C tar -tzf "${CODE_ARCHIVE}" >/dev/null

if [[ -z "${TARGET_DIR}" ]]; then
  TARGET_DIR="${BACKUP_ROOT}/restored_code_${TIMESTAMP:-$(timestamp_now)}"
fi

if [[ "${TARGET_DIR}" != /* ]]; then
  TARGET_DIR="${ROOT_DIR}/${TARGET_DIR}"
fi

if [[ -d "${TARGET_DIR}" ]] && find "${TARGET_DIR}" -mindepth 1 -maxdepth 1 | read -r _; then
  [[ "${YES}" -eq 1 ]] || die "La carpeta destino ${TARGET_DIR} no está vacía. Usa --yes."
fi

mkdir -p "${TARGET_DIR}"
LC_ALL=C tar -xzf "${CODE_ARCHIVE}" -C "${TARGET_DIR}"

log "Código restaurado."
log "Destino: ${TARGET_DIR}"
