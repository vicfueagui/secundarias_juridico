#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="$(cd "${ROOT_DIR}/.." && pwd)/project_secu_juridi_dev"
DELETE_MODE=0

usage() {
  cat <<'EOF'
Uso:
  scripts/dev/sync_to_parallel_clone.sh [--target-dir RUTA] [--delete]

Objetivo:
  - copiar cambios del repo con Git al clon operativo
  - preservar la configuración propia del clon (.env, override compose)
  - evitar copiar basura pesada o respaldos
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-dir)
      TARGET_DIR="${2:-}"
      shift 2
      ;;
    --delete)
      DELETE_MODE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Error: opción no reconocida: %s\n' "$1" >&2
      exit 1
      ;;
  esac
done

command -v rsync >/dev/null 2>&1 || {
  printf 'Error: no se encontró rsync.\n' >&2
  exit 1
}

if [[ "${TARGET_DIR}" != /* ]]; then
  TARGET_DIR="${ROOT_DIR}/${TARGET_DIR}"
fi

[[ -d "${TARGET_DIR}" ]] || {
  printf 'Error: no existe el clon destino: %s\n' "${TARGET_DIR}" >&2
  exit 1
}

printf '>> Sincronizando código hacia %s\n' "${TARGET_DIR}"

if [[ "${DELETE_MODE}" -eq 1 ]]; then
  rsync -a --delete \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='node_modules' \
    --exclude='staticfiles' \
    --exclude='/backups/' \
    --exclude='media' \
    --exclude='logs' \
    --exclude='smoke_test_reports' \
    --exclude='*.dump' \
    --exclude='*.tar.gz' \
    --exclude='*.log' \
    --exclude='.DS_Store' \
    --exclude='.env' \
    --exclude='docker-compose.override.yml' \
    --exclude='.clone_source_commit' \
    --exclude='.clone_source_status' \
    "${ROOT_DIR}/" "${TARGET_DIR}/"
else
  rsync -a \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='node_modules' \
    --exclude='staticfiles' \
    --exclude='/backups/' \
    --exclude='media' \
    --exclude='logs' \
    --exclude='smoke_test_reports' \
    --exclude='*.dump' \
    --exclude='*.tar.gz' \
    --exclude='*.log' \
    --exclude='.DS_Store' \
    --exclude='.env' \
    --exclude='docker-compose.override.yml' \
    --exclude='.clone_source_commit' \
    --exclude='.clone_source_status' \
    "${ROOT_DIR}/" "${TARGET_DIR}/"
fi

printf '>> Sincronización lista.\n'
printf '>> Siguiente paso en el clon:\n'
printf '   cd %s\n' "${TARGET_DIR}"
printf '   docker compose up -d --build web worker nginx\n'
printf '   docker compose exec -T web python manage.py check\n'
