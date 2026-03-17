#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

init_backup_context

CODE_ARCHIVE="${BACKUP_RUN_DIR}/${PROJECT_SLUG}_${ENV_SLUG}_code_${TIMESTAMP}.tar.gz"
GIT_BUNDLE="${BACKUP_RUN_DIR}/${PROJECT_SLUG}_${ENV_SLUG}_git_${TIMESTAMP}.bundle"
GIT_STATUS_FILE="${BACKUP_RUN_DIR}/git_status.txt"
GIT_UNTRACKED_FILE="${BACKUP_RUN_DIR}/git_untracked.txt"
GIT_DIFF_FILE="${BACKUP_RUN_DIR}/git_diff.patch"
GIT_STAGED_DIFF_FILE="${BACKUP_RUN_DIR}/git_staged.patch"

log "Generando respaldo del código fuente en ${CODE_ARCHIVE}"
LC_ALL=C tar -czf "${CODE_ARCHIVE}" \
  --exclude='.git' \
  --exclude='.env' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='.mypy_cache' \
  --exclude='node_modules' \
  --exclude='staticfiles' \
  --exclude='media' \
  --exclude='backups' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='*.dump' \
  --exclude='*.tar.gz' \
  --exclude='.DS_Store' \
  --exclude='smoke_test_reports' \
  -C "${ROOT_DIR}" .

LC_ALL=C tar -tzf "${CODE_ARCHIVE}" >/dev/null

CODE_HASH="$(set_checksum_entry "${CODE_ARCHIVE}")"
set_manifest "code_backup" "${CODE_ARCHIVE}"
set_manifest "code_sha256" "${CODE_HASH}"
set_manifest "code_size_bytes" "$(file_size_bytes "${CODE_ARCHIVE}")"

if git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "${ROOT_DIR}" status --short --branch > "${GIT_STATUS_FILE}"
  git -C "${ROOT_DIR}" ls-files --others --exclude-standard > "${GIT_UNTRACKED_FILE}"

  git -C "${ROOT_DIR}" diff --binary > "${GIT_DIFF_FILE}"
  if [[ ! -s "${GIT_DIFF_FILE}" ]]; then
    rm -f "${GIT_DIFF_FILE}"
  fi

  git -C "${ROOT_DIR}" diff --cached --binary > "${GIT_STAGED_DIFF_FILE}"
  if [[ ! -s "${GIT_STAGED_DIFF_FILE}" ]]; then
    rm -f "${GIT_STAGED_DIFF_FILE}"
  fi

  if git -C "${ROOT_DIR}" bundle create "${GIT_BUNDLE}" --all >/dev/null 2>&1; then
    GIT_BUNDLE_HASH="$(set_checksum_entry "${GIT_BUNDLE}")"
    set_manifest "git_bundle" "${GIT_BUNDLE}"
    set_manifest "git_bundle_sha256" "${GIT_BUNDLE_HASH}"
    set_manifest "git_bundle_size_bytes" "$(file_size_bytes "${GIT_BUNDLE}")"
  else
    warn "No fue posible generar git bundle. Se conserva el respaldo tar.gz del código."
  fi
fi

log "Respaldo de código listo."
log "Archivo: ${CODE_ARCHIVE}"
log "SHA256: ${CODE_HASH}"
