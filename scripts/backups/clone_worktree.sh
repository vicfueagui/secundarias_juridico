#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

MODE="auto"
TARGET_DIR="$(cd "${ROOT_DIR}/.." && pwd)/${PROJECT_NAME}_dev"
BRANCH_NAME="worktree/$(date +%Y%m%d_%H%M)"
REF_NAME="HEAD"

usage() {
  cat <<'EOF'
Uso:
  scripts/backups/clone_worktree.sh [--mode auto|worktree|copy] [--target-dir RUTA] [--branch NOMBRE] [--ref REF]

Comportamiento:
  - auto: usa git worktree si el árbol está limpio; si no, hace copia hermana con rsync
  - worktree: obliga git worktree
  - copy: hace copia hermana del working tree actual
EOF
}

git_tree_dirty() {
  if ! git -C "${ROOT_DIR}" diff --quiet; then
    return 0
  fi

  if ! git -C "${ROOT_DIR}" diff --cached --quiet; then
    return 0
  fi

  [[ -n "$(git -C "${ROOT_DIR}" ls-files --others --exclude-standard)" ]]
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --target-dir)
      TARGET_DIR="${2:-}"
      shift 2
      ;;
    --branch)
      BRANCH_NAME="${2:-}"
      shift 2
      ;;
    --ref)
      REF_NAME="${2:-}"
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

git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Este repositorio no está bajo Git."

if [[ "${TARGET_DIR}" != /* ]]; then
  TARGET_DIR="${ROOT_DIR}/${TARGET_DIR}"
fi

[[ ! -e "${TARGET_DIR}" ]] || die "La ruta destino ya existe: ${TARGET_DIR}"

case "${MODE}" in
  auto)
    if git_tree_dirty; then
      MODE="copy"
    else
      MODE="worktree"
    fi
    ;;
  worktree|copy)
    ;;
  *)
    die "Modo no reconocido: ${MODE}"
    ;;
esac

if [[ "${MODE}" == "worktree" ]]; then
  git_tree_dirty && die "El árbol tiene cambios locales. Congela commit/tag primero o usa --mode copy."
  log "Creando worktree en ${TARGET_DIR}"
  git -C "${ROOT_DIR}" worktree add "${TARGET_DIR}" -b "${BRANCH_NAME}" "${REF_NAME}"
  log "Worktree listo."
  log "Branch: ${BRANCH_NAME}"
  exit 0
fi

require_cmd rsync
mkdir -p "$(dirname "${TARGET_DIR}")"

log "Creando copia hermana del working tree actual en ${TARGET_DIR}"
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
  --exclude='*.dump' \
  --exclude='*.tar.gz' \
  --exclude='*.log' \
  --exclude='.DS_Store' \
  --exclude='smoke_test_reports' \
  "${ROOT_DIR}/" "${TARGET_DIR}/"

git -C "${ROOT_DIR}" rev-parse --short HEAD > "${TARGET_DIR}/.clone_source_commit"
git -C "${ROOT_DIR}" status --short --branch > "${TARGET_DIR}/.clone_source_status"

log "Copia hermana lista."
log "Destino: ${TARGET_DIR}"
