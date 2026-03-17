#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PROJECT_NAME="$(basename "${ROOT_DIR}")"
PROJECT_SLUG="$(printf '%s' "${PROJECT_NAME}" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9._-' '_')"
BACKUP_ROOT="${BACKUP_ROOT:-${ROOT_DIR}/backups}"
DB_SERVICE="${DB_SERVICE:-db}"
WEB_SERVICE="${WEB_SERVICE:-web}"
DEFAULT_COMPOSE_FILE="${ROOT_DIR}/docker-compose.yml"
LEGACY_COMPOSE_FILE="${ROOT_DIR}/docker/docker-compose.yml"
LATEST_LINK="${BACKUP_ROOT}/latest"

log() {
  printf '>> %s\n' "$*"
}

warn() {
  printf '>> Aviso: %s\n' "$*" >&2
}

die() {
  printf '>> Error: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "No se encontró el comando '$1'."
}

pg_tool_major_version() {
  local binary="$1"
  local version_text=""

  [[ -x "${binary}" ]] || {
    printf '0\n'
    return 0
  }

  version_text="$("${binary}" --version 2>/dev/null || true)"
  if [[ "${version_text}" =~ ([0-9]+)(\.[0-9]+)? ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
  else
    printf '0\n'
  fi
}

resolve_pg_tool() {
  local tool="$1"
  local cache_var="$2"
  local current="${!cache_var:-}"
  local candidate=""
  local best=""
  local best_version="-1"
  local candidate_version=0

  if [[ -n "${current}" && -x "${current}" ]]; then
    printf '%s\n' "${current}"
    return 0
  fi

  while IFS= read -r candidate; do
    [[ -n "${candidate}" && -x "${candidate}" ]] || continue
    candidate_version="$(pg_tool_major_version "${candidate}")"
    if (( candidate_version > best_version )); then
      best="${candidate}"
      best_version="${candidate_version}"
    fi
  done < <(type -aP "${tool}" 2>/dev/null || true)

  for candidate in "/opt/homebrew/opt/libpq/bin/${tool}" "/usr/local/opt/libpq/bin/${tool}"; do
    [[ -n "${candidate}" && -x "${candidate}" ]] || continue
    candidate_version="$(pg_tool_major_version "${candidate}")"
    if (( candidate_version > best_version )); then
      best="${candidate}"
      best_version="${candidate_version}"
    fi
  done

  shopt -s nullglob
  for candidate in /Library/PostgreSQL/*/bin/"${tool}"; do
    [[ -n "${candidate}" && -x "${candidate}" ]] || continue
    candidate_version="$(pg_tool_major_version "${candidate}")"
    if (( candidate_version > best_version )); then
      best="${candidate}"
      best_version="${candidate_version}"
    fi
  done
  shopt -u nullglob

  [[ -n "${best}" ]] || return 1
  printf -v "${cache_var}" '%s' "${best}"
  export "${cache_var}"
  printf '%s\n' "${best}"
}

require_pg_tool() {
  local tool="$1"
  local cache_var="$2"
  resolve_pg_tool "${tool}" "${cache_var}" >/dev/null 2>&1 || die "No se encontró un binario utilizable para '${tool}'."
}

load_env() {
  if [[ -f "${ROOT_DIR}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${ROOT_DIR}/.env" >/dev/null 2>&1 || true
    set +a
  fi

  DJANGO_ENV="${DJANGO_ENV:-development}"
  POSTGRES_DB="${POSTGRES_DB:-cejei_licencias}"
  POSTGRES_USER="${POSTGRES_USER:-cejei}"
  POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
  POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
  POSTGRES_PORT="${POSTGRES_PORT:-5432}"
}

sanitize_token() {
  printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9._-' '_'
}

trim_spaces() {
  local value="${1:-}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "${value}"
}

timestamp_now() {
  date +%Y%m%d_%H%M%S
}

date_from_timestamp() {
  local ts="$1"
  printf '%s-%s-%s' "${ts:0:4}" "${ts:4:2}" "${ts:6:2}"
}

docker_installed() {
  command -v docker >/dev/null 2>&1
}

compose_service_running() {
  local file="$1"
  local service="$2"
  [[ -n "${file}" && -f "${file}" ]] || return 1
  docker compose -f "${file}" ps --status running --services 2>/dev/null | grep -qx "${service}"
}

ensure_compose_service_running() {
  local file="$1"
  local service="$2"
  compose_service_running "${file}" "${service}" || die "El servicio '${service}' no está corriendo en ${file}."
}

detect_compose_file() {
  local file=""

  if [[ -n "${COMPOSE_FILE:-}" ]]; then
    [[ -f "${COMPOSE_FILE}" ]] || die "COMPOSE_FILE no existe: ${COMPOSE_FILE}"
    printf '%s\n' "${COMPOSE_FILE}"
    return 0
  fi

  for file in "${DEFAULT_COMPOSE_FILE}" "${LEGACY_COMPOSE_FILE}"; do
    [[ -f "${file}" ]] || continue
    if docker_installed && compose_service_running "${file}" "${DB_SERVICE}"; then
      printf '%s\n' "${file}"
      return 0
    fi
  done

  if [[ -f "${DEFAULT_COMPOSE_FILE}" ]]; then
    printf '%s\n' "${DEFAULT_COMPOSE_FILE}"
    return 0
  fi

  if [[ -f "${LEGACY_COMPOSE_FILE}" ]]; then
    printf '%s\n' "${LEGACY_COMPOSE_FILE}"
    return 0
  fi

  return 1
}

resolve_compose_file_or_die() {
  local file=""
  file="$(detect_compose_file || true)"
  [[ -n "${file}" ]] || die "No se encontró un archivo compose utilizable."
  printf '%s\n' "${file}"
}

direct_db_ready() {
  local pg_isready_bin=""
  load_env
  pg_isready_bin="$(resolve_pg_tool pg_isready PG_ISREADY_BIN)" || return 1
  PGPASSWORD="${POSTGRES_PASSWORD}" \
    "${pg_isready_bin}" -q -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"
}

detect_db_mode() {
  local requested="${DB_BACKUP_MODE:-${BACKUP_MODE:-auto}}"
  local compose_file=""

  case "${requested}" in
    docker)
      printf 'docker\n'
      ;;
    direct)
      printf 'direct\n'
      ;;
    auto)
      if docker_installed; then
        compose_file="$(detect_compose_file || true)"
        if [[ -n "${compose_file}" ]] && compose_service_running "${compose_file}" "${DB_SERVICE}"; then
          printf 'docker\n'
          return 0
        fi
      fi

      if direct_db_ready; then
        printf 'direct\n'
        return 0
      fi

      die "No fue posible detectar una conexión PostgreSQL operativa. Usa Docker o ajusta POSTGRES_*."
      ;;
    *)
      die "Modo de base de datos no reconocido: ${requested}. Usa docker, direct o auto."
      ;;
  esac
}

resolve_host_media_dir() {
  local candidate=""

  load_env

  if [[ -n "${DJANGO_MEDIA_ROOT:-}" ]]; then
    if [[ "${DJANGO_MEDIA_ROOT}" = /* ]]; then
      candidate="${DJANGO_MEDIA_ROOT}"
    else
      candidate="${ROOT_DIR}/${DJANGO_MEDIA_ROOT}"
    fi
    [[ -d "${candidate}" ]] && {
      printf '%s\n' "${candidate}"
      return 0
    }
  fi

  candidate="${ROOT_DIR}/media"
  [[ -d "${candidate}" ]] && {
    printf '%s\n' "${candidate}"
    return 0
  }

  return 1
}

detect_media_mode() {
  local requested="${MEDIA_BACKUP_MODE:-auto}"
  local compose_file=""

  case "${requested}" in
    docker)
      printf 'docker\n'
      ;;
    host)
      printf 'host\n'
      ;;
    none)
      printf 'none\n'
      ;;
    auto)
      if docker_installed; then
        compose_file="$(detect_compose_file || true)"
        if [[ -n "${compose_file}" ]] && compose_service_running "${compose_file}" "${WEB_SERVICE}"; then
          printf 'docker\n'
          return 0
        fi
      fi

      if resolve_host_media_dir >/dev/null 2>&1; then
        printf 'host\n'
      else
        printf 'none\n'
      fi
      ;;
    *)
      die "Modo de media no reconocido: ${requested}. Usa docker, host, none o auto."
      ;;
  esac
}

ensure_safe_db_name() {
  [[ "${1:-}" =~ ^[A-Za-z0-9_]+$ ]] || die "Nombre de base no seguro: ${1:-<vacío>}."
}

set_manifest() {
  local key="$1"
  local value="${2:-}"
  local tmp_file=""

  touch "${MANIFEST_FILE}"
  tmp_file="${MANIFEST_FILE}.tmp.$$"

  awk -v key="${key}" -v value="${value}" -F= '
    BEGIN { done = 0 }
    $1 == key {
      print key "=" value
      done = 1
      next
    }
    { print }
    END {
      if (!done) {
        print key "=" value
      }
    }
  ' "${MANIFEST_FILE}" > "${tmp_file}"

  mv "${tmp_file}" "${MANIFEST_FILE}"
}

manifest_get() {
  local key="$1"
  [[ -f "${MANIFEST_FILE}" ]] || return 1
  awk -F= -v key="${key}" '$1 == key { print substr($0, index($0, "=") + 1) }' "${MANIFEST_FILE}" | tail -n 1
}

ensure_manifest_defaults() {
  touch "${MANIFEST_FILE}"
  set_manifest "project_name" "${PROJECT_NAME}"
  set_manifest "project_slug" "${PROJECT_SLUG}"
  set_manifest "django_env" "${DJANGO_ENV}"
  set_manifest "timestamp" "${TIMESTAMP}"
  set_manifest "backup_run_dir" "${BACKUP_RUN_DIR}"

  if git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    set_manifest "git_branch" "$(git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    set_manifest "git_commit" "$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || true)"
    if git -C "${ROOT_DIR}" diff --quiet && git -C "${ROOT_DIR}" diff --cached --quiet && [[ -z "$(git -C "${ROOT_DIR}" ls-files --others --exclude-standard)" ]]; then
      set_manifest "git_dirty" "no"
    else
      set_manifest "git_dirty" "si"
    fi
  else
    set_manifest "git_branch" "sin_git"
    set_manifest "git_commit" "sin_git"
    set_manifest "git_dirty" "sin_git"
  fi
}

init_backup_context() {
  load_env

  TIMESTAMP="${TIMESTAMP:-$(timestamp_now)}"
  BACKUP_DATE="${BACKUP_DATE:-$(date_from_timestamp "${TIMESTAMP}")}"
  ENV_SLUG="${ENV_SLUG:-$(sanitize_token "${DJANGO_ENV}")}"
  [[ -n "${ENV_SLUG}" ]] || ENV_SLUG="development"

  BACKUP_RUN_DIR="${BACKUP_RUN_DIR:-${BACKUP_ROOT}/${BACKUP_DATE}/${PROJECT_SLUG}_${ENV_SLUG}_${TIMESTAMP}}"
  if [[ "${BACKUP_RUN_DIR}" != /* ]]; then
    BACKUP_RUN_DIR="${ROOT_DIR}/${BACKUP_RUN_DIR}"
  fi

  MANIFEST_FILE="${BACKUP_RUN_DIR}/manifest.env"
  CHECKSUM_FILE="${BACKUP_RUN_DIR}/checksums.sha256"

  mkdir -p "${BACKUP_RUN_DIR}"
  ensure_manifest_defaults
  update_latest_symlink
}

update_latest_symlink() {
  mkdir -p "${BACKUP_ROOT}"
  ln -sfn "${BACKUP_RUN_DIR}" "${LATEST_LINK}"
}

latest_backup_dir() {
  if [[ -e "${LATEST_LINK}" ]]; then
    (cd "${LATEST_LINK}" && pwd)
    return 0
  fi

  find "${BACKUP_ROOT}" -mindepth 2 -maxdepth 2 -type d | sort | tail -n 1
}

resolve_run_dir() {
  local input="${1:-}"

  if [[ -z "${input}" ]]; then
    input="$(latest_backup_dir || true)"
  fi

  [[ -n "${input}" ]] || die "No se encontró un respaldo para trabajar."

  if [[ -f "${input}" ]]; then
    input="$(dirname "${input}")"
  fi

  if [[ "${input}" != /* ]]; then
    input="$(cd "$(dirname "${input}")" && pwd)/$(basename "${input}")"
  fi

  [[ -d "${input}" ]] || die "La ruta indicada no es un directorio válido: ${input}"
  printf '%s\n' "${input}"
}

resolve_artifact_in_run_dir() {
  local run_dir="$1"
  local pattern="$2"
  find "${run_dir}" -maxdepth 1 -type f -name "${pattern}" | sort | head -n 1
}

sha256_of_file() {
  local file_path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${file_path}" | awk '{print $1}'
  else
    require_cmd shasum
    shasum -a 256 "${file_path}" | awk '{print $1}'
  fi
}

set_checksum_entry() {
  local file_path="$1"
  local base_name=""
  local hash_value=""
  local tmp_file=""

  [[ -f "${file_path}" ]] || die "No existe el archivo para checksum: ${file_path}"

  base_name="$(basename "${file_path}")"
  hash_value="$(sha256_of_file "${file_path}")"
  tmp_file="${CHECKSUM_FILE}.tmp.$$"

  touch "${CHECKSUM_FILE}"
  awk -v base_name="${base_name}" '$2 != base_name { print }' "${CHECKSUM_FILE}" > "${tmp_file}"
  printf '%s  %s\n' "${hash_value}" "${base_name}" >> "${tmp_file}"
  mv "${tmp_file}" "${CHECKSUM_FILE}"

  printf '%s\n' "${hash_value}"
}

file_size_bytes() {
  wc -c < "$1" | tr -d ' '
}

env_file_get_value() {
  local file_path="$1"
  local key="$2"
  [[ -f "${file_path}" ]] || return 1
  awk -F= -v key="${key}" '$1 == key { print substr($0, index($0, "=") + 1) }' "${file_path}" | tail -n 1
}

set_env_file_value() {
  local file_path="$1"
  local key="$2"
  local value="${3:-}"
  local tmp_file=""

  mkdir -p "$(dirname "${file_path}")"
  [[ -f "${file_path}" ]] || : > "${file_path}"
  tmp_file="${file_path}.tmp.$$"

  awk -v key="${key}" -v value="${value}" -F= '
    BEGIN { done = 0 }
    $1 == key {
      print key "=" value
      done = 1
      next
    }
    { print }
    END {
      if (!done) {
        print key "=" value
      }
    }
  ' "${file_path}" > "${tmp_file}"

  mv "${tmp_file}" "${file_path}"
}

csv_union() {
  local item=""
  local part=""
  local normalized=""
  local result=()
  local seen="|"

  for item in "$@"; do
    [[ -n "${item}" ]] || continue
    IFS=',' read -r -a __csv_parts <<< "${item}"
    for part in "${__csv_parts[@]}"; do
      normalized="$(trim_spaces "${part}")"
      [[ -n "${normalized}" ]] || continue
      case "${seen}" in
        *"|${normalized}|"*) ;;
        *)
          result+=("${normalized}")
          seen="${seen}${normalized}|"
          ;;
      esac
    done
  done

  if [[ "${#result[@]}" -eq 0 ]]; then
    printf '\n'
    return 0
  fi

  local joined=""
  local idx=0
  for idx in "${!result[@]}"; do
    if [[ "${idx}" -gt 0 ]]; then
      joined+=","
    fi
    joined+="${result[${idx}]}"
  done
  printf '%s\n' "${joined}"
}

db_query_value() {
  local mode="$1"
  local database="$2"
  local sql="$3"
  local compose_file=""
  local psql_bin=""

  load_env

  case "${mode}" in
    docker)
      compose_file="${COMPOSE_FILE_RESOLVED:-$(resolve_compose_file_or_die)}"
      ensure_compose_service_running "${compose_file}" "${DB_SERVICE}"
      docker compose -f "${compose_file}" exec -T "${DB_SERVICE}" sh -lc \
        "export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"; psql -v ON_ERROR_STOP=1 -U \"\${POSTGRES_USER}\" -d \"${database}\" -tAc \"${sql}\"" \
        | tr -d ' \r'
      ;;
    direct)
      require_pg_tool psql PSQL_BIN
      psql_bin="$(resolve_pg_tool psql PSQL_BIN)"
      PGPASSWORD="${POSTGRES_PASSWORD}" \
        "${psql_bin}" -v ON_ERROR_STOP=1 -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${database}" -tAc "${sql}" \
        | tr -d ' \r'
      ;;
    *)
      die "Modo de consulta DB no soportado: ${mode}"
      ;;
  esac
}

database_exists() {
  local mode="$1"
  local database="$2"
  local exists=""

  ensure_safe_db_name "${database}"
  exists="$(db_query_value "${mode}" "postgres" "SELECT 1 FROM pg_database WHERE datname='${database}';" || true)"
  [[ "${exists}" == "1" ]]
}

drop_database() {
  local mode="$1"
  local database="$2"
  local sql=""
  local compose_file=""
  local psql_bin=""

  ensure_safe_db_name "${database}"
  sql="DROP DATABASE IF EXISTS \"${database}\" WITH (FORCE);"
  load_env

  case "${mode}" in
    docker)
      compose_file="${COMPOSE_FILE_RESOLVED:-$(resolve_compose_file_or_die)}"
      ensure_compose_service_running "${compose_file}" "${DB_SERVICE}"
      docker compose -f "${compose_file}" exec -T "${DB_SERVICE}" sh -lc \
        "export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"; psql -v ON_ERROR_STOP=1 -U \"\${POSTGRES_USER}\" -d postgres -c '${sql}'" \
        >/dev/null
      ;;
    direct)
      require_pg_tool psql PSQL_BIN
      psql_bin="$(resolve_pg_tool psql PSQL_BIN)"
      PGPASSWORD="${POSTGRES_PASSWORD}" \
        "${psql_bin}" -v ON_ERROR_STOP=1 -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres -c "${sql}" \
        >/dev/null
      ;;
    *)
      die "Modo de drop DB no soportado: ${mode}"
      ;;
  esac
}

create_database() {
  local mode="$1"
  local database="$2"
  local sql=""
  local compose_file=""
  local psql_bin=""

  ensure_safe_db_name "${database}"
  sql="CREATE DATABASE \"${database}\";"
  load_env

  case "${mode}" in
    docker)
      compose_file="${COMPOSE_FILE_RESOLVED:-$(resolve_compose_file_or_die)}"
      ensure_compose_service_running "${compose_file}" "${DB_SERVICE}"
      docker compose -f "${compose_file}" exec -T "${DB_SERVICE}" sh -lc \
        "export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"; psql -v ON_ERROR_STOP=1 -U \"\${POSTGRES_USER}\" -d postgres -c '${sql}'" \
        >/dev/null
      ;;
    direct)
      require_pg_tool psql PSQL_BIN
      psql_bin="$(resolve_pg_tool psql PSQL_BIN)"
      PGPASSWORD="${POSTGRES_PASSWORD}" \
        "${psql_bin}" -v ON_ERROR_STOP=1 -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres -c "${sql}" \
        >/dev/null
      ;;
    *)
      die "Modo de create DB no soportado: ${mode}"
      ;;
  esac
}

restore_dump_to_db() {
  local mode="$1"
  local dump_file="$2"
  local database="$3"
  local compose_file=""
  local pg_restore_bin=""

  [[ -f "${dump_file}" ]] || die "No existe el dump a restaurar: ${dump_file}"
  ensure_safe_db_name "${database}"
  load_env

  case "${mode}" in
    docker)
      compose_file="${COMPOSE_FILE_RESOLVED:-$(resolve_compose_file_or_die)}"
      ensure_compose_service_running "${compose_file}" "${DB_SERVICE}"
      docker compose -f "${compose_file}" exec -T "${DB_SERVICE}" sh -lc \
        "export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"; pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error -U \"\${POSTGRES_USER}\" -d \"${database}\"" \
        < "${dump_file}"
      ;;
    direct)
      require_pg_tool pg_restore PG_RESTORE_BIN
      pg_restore_bin="$(resolve_pg_tool pg_restore PG_RESTORE_BIN)"
      PGPASSWORD="${POSTGRES_PASSWORD}" \
        "${pg_restore_bin}" --clean --if-exists --no-owner --no-privileges --exit-on-error \
        -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${database}" "${dump_file}"
      ;;
    *)
      die "Modo de restore DB no soportado: ${mode}"
      ;;
  esac
}
