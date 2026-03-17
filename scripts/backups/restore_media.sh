#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

INPUT_PATH=""
TARGET_DIR=""
APPLY_DOCKER_LIVE=0
YES=0

usage() {
  cat <<'EOF'
Uso:
  scripts/backups/restore_media.sh [ruta_respaldo|ruta_media.tar.gz] [--target-dir RUTA] [--docker-live] [--yes]

Notas:
  - Sin --docker-live, restaura a una carpeta segura en host.
  - Con --docker-live, reemplaza /app/media del servicio web activo y exige --yes.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-dir)
      TARGET_DIR="${2:-}"
      shift 2
      ;;
    --docker-live)
      APPLY_DOCKER_LIVE=1
      shift
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

TIMESTAMP="${TIMESTAMP:-$(timestamp_now)}"

if [[ -n "${INPUT_PATH}" && -f "${INPUT_PATH}" ]]; then
  MEDIA_ARCHIVE="${INPUT_PATH}"
else
  RUN_DIR="$(resolve_run_dir "${INPUT_PATH}")"
  MANIFEST_FILE="${RUN_DIR}/manifest.env"
  MEDIA_ARCHIVE="$(manifest_get "media_backup" || true)"
  [[ -n "${MEDIA_ARCHIVE}" && -f "${MEDIA_ARCHIVE}" ]] || MEDIA_ARCHIVE="$(resolve_artifact_in_run_dir "${RUN_DIR}" '*_media_*.tar.gz')"
  MEDIA_NOTE="$(manifest_get "media_note" || true)"
  [[ -n "${MEDIA_NOTE}" && -f "${MEDIA_NOTE}" ]] || MEDIA_NOTE="$(resolve_artifact_in_run_dir "${RUN_DIR}" 'media_backup_skipped.txt')"
fi

if [[ -z "${MEDIA_ARCHIVE:-}" || ! -f "${MEDIA_ARCHIVE}" ]]; then
  if [[ -n "${MEDIA_NOTE:-}" && -f "${MEDIA_NOTE}" ]]; then
    die "Ese respaldo documentó que no había media aplicable para restaurar."
  fi
  die "No se encontró archive de media."
fi

LC_ALL=C tar -tzf "${MEDIA_ARCHIVE}" >/dev/null

if [[ "${APPLY_DOCKER_LIVE}" -eq 1 ]]; then
  [[ "${YES}" -eq 1 ]] || die "Restaurar media sobre el contenedor activo requiere --yes."
  require_cmd docker
  COMPOSE_FILE_RESOLVED="$(resolve_compose_file_or_die)"
  ensure_compose_service_running "${COMPOSE_FILE_RESOLVED}" "${WEB_SERVICE}"
  log "Reemplazando /app/media del servicio ${WEB_SERVICE}"
  docker compose -f "${COMPOSE_FILE_RESOLVED}" exec -T "${WEB_SERVICE}" sh -lc 'rm -rf /app/media/* && mkdir -p /app/media'
  docker compose -f "${COMPOSE_FILE_RESOLVED}" exec -T "${WEB_SERVICE}" sh -lc 'export LC_ALL=C; cd /app && tar -xzf -' < "${MEDIA_ARCHIVE}"
  log "Media restaurada sobre el contenedor activo."
  exit 0
fi

if [[ -z "${TARGET_DIR}" ]]; then
  TARGET_DIR="${BACKUP_ROOT}/restored_media_${TIMESTAMP}"
fi

if [[ "${TARGET_DIR}" != /* ]]; then
  TARGET_DIR="${ROOT_DIR}/${TARGET_DIR}"
fi

if [[ -d "${TARGET_DIR}" ]] && find "${TARGET_DIR}" -mindepth 1 -maxdepth 1 | read -r _; then
  [[ "${YES}" -eq 1 ]] || die "La carpeta destino ${TARGET_DIR} no está vacía. Usa --yes para reutilizarla."
fi

mkdir -p "${TARGET_DIR}"
LC_ALL=C tar -xzf "${MEDIA_ARCHIVE}" -C "${TARGET_DIR}"

log "Media restaurada en host."
log "Destino: ${TARGET_DIR}"
