#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

usage() {
  cat <<'EOF'
Uso:
  scripts/backups/backup_media.sh [--mode docker|host|auto|none]

Opciones:
  --mode   Fuerza el origen de archivos adjuntos.
           - docker: usa /app/media del servicio web activo
           - host: usa la carpeta local media/ o DJANGO_MEDIA_ROOT si existe
           - auto: detecta automáticamente (default)
           - none: solo documenta que no se respaldará media
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MEDIA_BACKUP_MODE="${2:-}"
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

MEDIA_MODE="$(detect_media_mode)"
ARCHIVE_FILE="${BACKUP_RUN_DIR}/${PROJECT_SLUG}_${ENV_SLUG}_media_${TIMESTAMP}.tar.gz"
NOTE_FILE="${BACKUP_RUN_DIR}/media_backup_skipped.txt"

set_manifest "media_mode" "${MEDIA_MODE}"

case "${MEDIA_MODE}" in
  docker)
    require_cmd docker
    COMPOSE_FILE_RESOLVED="$(resolve_compose_file_or_die)"
    ensure_compose_service_running "${COMPOSE_FILE_RESOLVED}" "${WEB_SERVICE}"
    docker compose -f "${COMPOSE_FILE_RESOLVED}" exec -T "${WEB_SERVICE}" sh -lc '[ -d /app/media ]' \
      || die "El servicio web no tiene /app/media disponible."
    MEDIA_COUNT="$(docker compose -f "${COMPOSE_FILE_RESOLVED}" exec -T "${WEB_SERVICE}" sh -lc 'find /app/media -type f | wc -l' | tr -d ' \r')"
    log "Generando respaldo de media desde Docker en ${ARCHIVE_FILE}"
    docker compose -f "${COMPOSE_FILE_RESOLVED}" exec -T "${WEB_SERVICE}" sh -lc 'export LC_ALL=C; cd /app && tar -czf - media' > "${ARCHIVE_FILE}"
    set_manifest "media_source" "docker:${WEB_SERVICE}:/app/media"
    set_manifest "media_compose_file" "${COMPOSE_FILE_RESOLVED}"
    ;;
  host)
    MEDIA_SOURCE_DIR="$(resolve_host_media_dir || true)"
    [[ -n "${MEDIA_SOURCE_DIR}" ]] || die "No se encontró carpeta local de media para respaldar."
    MEDIA_COUNT="$(find "${MEDIA_SOURCE_DIR}" -type f | wc -l | tr -d ' ')"
    log "Generando respaldo de media desde host en ${ARCHIVE_FILE}"
    LC_ALL=C tar -czf "${ARCHIVE_FILE}" -C "$(dirname "${MEDIA_SOURCE_DIR}")" "$(basename "${MEDIA_SOURCE_DIR}")"
    set_manifest "media_source" "host:${MEDIA_SOURCE_DIR}"
    ;;
  none)
    printf 'No se encontró un origen de media aplicable en este entorno.\n' > "${NOTE_FILE}"
    set_manifest "media_note" "${NOTE_FILE}"
    log "No se generó archivo de media. Se documentó en ${NOTE_FILE}"
    exit 0
    ;;
  *)
    die "Modo de media no soportado: ${MEDIA_MODE}"
    ;;
esac

LC_ALL=C tar -tzf "${ARCHIVE_FILE}" >/dev/null

MEDIA_HASH="$(set_checksum_entry "${ARCHIVE_FILE}")"
set_manifest "media_backup" "${ARCHIVE_FILE}"
set_manifest "media_sha256" "${MEDIA_HASH}"
set_manifest "media_size_bytes" "$(file_size_bytes "${ARCHIVE_FILE}")"
set_manifest "media_file_count_source" "${MEDIA_COUNT:-0}"

log "Respaldo media listo."
log "Archivo: ${ARCHIVE_FILE}"
log "SHA256: ${MEDIA_HASH}"
