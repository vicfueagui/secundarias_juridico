#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

VERIFY_AFTER=0

usage() {
  cat <<'EOF'
Uso:
  scripts/backups/backup_full.sh [--verify]

Opciones:
  --verify   Ejecuta verify_backup.sh al terminar.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --verify)
      VERIFY_AFTER=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf '>> Error: opción no reconocida: %s\n' "$1" >&2
      exit 1
      ;;
  esac
done

TIMESTAMP="${TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}"
export TIMESTAMP
init_backup_context

export BACKUP_RUN_DIR TIMESTAMP

"${SCRIPT_DIR}/backup_db.sh"
"${SCRIPT_DIR}/backup_media.sh"
"${SCRIPT_DIR}/backup_code.sh"
"${SCRIPT_DIR}/backup_env.sh"

printf '>> Respaldo integral listo en %s\n' "${BACKUP_RUN_DIR}"

if [[ "${VERIFY_AFTER}" -eq 1 ]]; then
  "${SCRIPT_DIR}/verify_backup.sh" "${BACKUP_RUN_DIR}"
fi
