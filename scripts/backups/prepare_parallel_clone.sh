#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

TARGET_DIR="$(cd "${ROOT_DIR}/.." && pwd)/${PROJECT_NAME}_dev"
CLONE_MODE="auto"
BACKUP_SOURCE=""
CLONE_DB_NAME=""
CLONE_DB_PORT="5542"
CLONE_NGINX_PORT="8081"
CLONE_NGINX_PORT_LEGACY="8001"
SKIP_RESTORE=0
SKIP_START=0

clone_sanitized_env() {
  env \
    -u POSTGRES_DB \
    -u POSTGRES_USER \
    -u POSTGRES_PASSWORD \
    -u POSTGRES_HOST \
    -u POSTGRES_PORT \
    -u COMPOSE_PROJECT_NAME \
    -u NGINX_PORT \
    -u NGINX_PORT_LEGACY \
    -u WORKER_NAME \
    -u DJANGO_ALLOWED_HOSTS \
    -u DJANGO_CSRF_TRUSTED_ORIGINS \
    "$@"
}

clone_compose() {
  (
    cd "${TARGET_DIR}"
    clone_sanitized_env docker compose "$@"
  )
}

clone_script() {
  (
    cd "${TARGET_DIR}"
    clone_sanitized_env "$@"
  )
}

usage() {
  cat <<'EOF'
Uso:
  scripts/backups/prepare_parallel_clone.sh [--target-dir RUTA] [--backup-dir RUTA] [--mode auto|copy|worktree]
                                             [--db-name NOMBRE] [--db-port PUERTO]
                                             [--nginx-port PUERTO] [--nginx-port-legacy PUERTO]
                                             [--skip-start] [--skip-restore]

Objetivo:
  - crear un clon paralelo en carpeta hermana
  - ajustar .env para que no choque con el proyecto original
  - exponer PostgreSQL del clon en un puerto propio para trabajo local con .venv
  - levantar el stack del clon
  - restaurar DB y media desde el respaldo indicado
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-dir)
      TARGET_DIR="${2:-}"
      shift 2
      ;;
    --backup-dir)
      BACKUP_SOURCE="${2:-}"
      shift 2
      ;;
    --mode)
      CLONE_MODE="${2:-}"
      shift 2
      ;;
    --db-name)
      CLONE_DB_NAME="${2:-}"
      shift 2
      ;;
    --db-port)
      CLONE_DB_PORT="${2:-}"
      shift 2
      ;;
    --nginx-port)
      CLONE_NGINX_PORT="${2:-}"
      shift 2
      ;;
    --nginx-port-legacy)
      CLONE_NGINX_PORT_LEGACY="${2:-}"
      shift 2
      ;;
    --skip-start)
      SKIP_START=1
      shift
      ;;
    --skip-restore)
      SKIP_RESTORE=1
      shift
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

load_env
require_cmd docker
require_pg_tool pg_isready PG_ISREADY_BIN

[[ "${CLONE_NGINX_PORT}" != "${CLONE_NGINX_PORT_LEGACY}" ]] || die "NGINX_PORT y NGINX_PORT_LEGACY del clon no pueden ser iguales."
[[ "${CLONE_DB_PORT}" != "${POSTGRES_PORT}" ]] || warn "El puerto PostgreSQL del clon coincide con POSTGRES_PORT actual. Verifica que no haya conflicto."

if [[ -z "${BACKUP_SOURCE}" ]]; then
  BACKUP_SOURCE="$(latest_backup_dir || true)"
fi
BACKUP_SOURCE="$(resolve_run_dir "${BACKUP_SOURCE}")"

if [[ "${TARGET_DIR}" != /* ]]; then
  TARGET_DIR="${ROOT_DIR}/${TARGET_DIR}"
fi

if [[ -z "${CLONE_DB_NAME}" ]]; then
  CLONE_DB_NAME="${POSTGRES_DB}_dev"
fi

CLONE_PROJECT_NAME="$(sanitize_token "$(basename "${TARGET_DIR}")")"
[[ -n "${CLONE_PROJECT_NAME}" ]] || CLONE_PROJECT_NAME="${PROJECT_SLUG}_dev"

ORIGINAL_HOSTS="$(env_file_get_value "${ROOT_DIR}/.env" "DJANGO_ALLOWED_HOSTS" || true)"
ORIGINAL_CSRF="$(env_file_get_value "${ROOT_DIR}/.env" "DJANGO_CSRF_TRUSTED_ORIGINS" || true)"

log "Creando clon paralelo en ${TARGET_DIR}"
"${SCRIPT_DIR}/clone_worktree.sh" --mode "${CLONE_MODE}" --target-dir "${TARGET_DIR}"

CLONE_ENV_FILE="${TARGET_DIR}/.env"
if [[ ! -f "${CLONE_ENV_FILE}" && -f "${TARGET_DIR}/.env.example" ]]; then
  cp "${TARGET_DIR}/.env.example" "${CLONE_ENV_FILE}"
fi
[[ -f "${CLONE_ENV_FILE}" ]] || die "El clon no tiene .env ni .env.example para ajustar."

MERGED_HOSTS="$(csv_union "${ORIGINAL_HOSTS}" "localhost,127.0.0.1")"
MERGED_CSRF="$(csv_union "${ORIGINAL_CSRF}" "http://127.0.0.1:${CLONE_NGINX_PORT},http://localhost:${CLONE_NGINX_PORT},http://127.0.0.1:${CLONE_NGINX_PORT_LEGACY},http://localhost:${CLONE_NGINX_PORT_LEGACY}")"

set_env_file_value "${CLONE_ENV_FILE}" "COMPOSE_PROJECT_NAME" "${CLONE_PROJECT_NAME}"
set_env_file_value "${CLONE_ENV_FILE}" "POSTGRES_DB" "${CLONE_DB_NAME}"
set_env_file_value "${CLONE_ENV_FILE}" "POSTGRES_HOST" "127.0.0.1"
set_env_file_value "${CLONE_ENV_FILE}" "POSTGRES_PORT" "${CLONE_DB_PORT}"
set_env_file_value "${CLONE_ENV_FILE}" "NGINX_PORT" "${CLONE_NGINX_PORT}"
set_env_file_value "${CLONE_ENV_FILE}" "NGINX_PORT_LEGACY" "${CLONE_NGINX_PORT_LEGACY}"
set_env_file_value "${CLONE_ENV_FILE}" "WORKER_NAME" "${CLONE_PROJECT_NAME}-worker"
set_env_file_value "${CLONE_ENV_FILE}" "DJANGO_ALLOWED_HOSTS" "${MERGED_HOSTS}"
set_env_file_value "${CLONE_ENV_FILE}" "DJANGO_CSRF_TRUSTED_ORIGINS" "${MERGED_CSRF}"

OVERRIDE_FILE="${TARGET_DIR}/docker-compose.override.yml"
cat > "${OVERRIDE_FILE}" <<EOF
services:
  db:
    ports:
      - "${CLONE_DB_PORT}:5432"
EOF

CLONE_NOTE_FILE="${TARGET_DIR}/docs/CLON_LOCAL_LISTO.md"
mkdir -p "$(dirname "${CLONE_NOTE_FILE}")"
cat > "${CLONE_NOTE_FILE}" <<EOF
# Clon Local Listo

- Carpeta clon: ${TARGET_DIR}
- Respaldo base usado: ${BACKUP_SOURCE}
- URL principal: http://127.0.0.1:${CLONE_NGINX_PORT}
- URL compatibilidad: http://127.0.0.1:${CLONE_NGINX_PORT_LEGACY}
- PostgreSQL host: 127.0.0.1
- PostgreSQL puerto: ${CLONE_DB_PORT}
- Base de datos: ${CLONE_DB_NAME}

## Comandos útiles

\`\`\`bash
cd ${TARGET_DIR}
docker compose ps
docker compose logs -f web nginx
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py check
\`\`\`
EOF

if [[ "${SKIP_START}" -eq 1 ]]; then
  log "Clon creado y configurado. Arranque omitido por --skip-start."
  exit 0
fi

log "Levantando stack del clon ${CLONE_PROJECT_NAME}"
clone_compose up -d --build db redis

log "Esperando PostgreSQL del clon en 127.0.0.1:${CLONE_DB_PORT}"
TRIES=0
PG_ISREADY_BIN_PATH="$(resolve_pg_tool pg_isready PG_ISREADY_BIN)"
until PGPASSWORD="$(env_file_get_value "${CLONE_ENV_FILE}" "POSTGRES_PASSWORD" || true)" \
  "${PG_ISREADY_BIN_PATH}" -q -h 127.0.0.1 -p "${CLONE_DB_PORT}" -U "$(env_file_get_value "${CLONE_ENV_FILE}" "POSTGRES_USER" || printf 'cejei')" -d postgres; do
  TRIES=$((TRIES + 1))
  [[ "${TRIES}" -lt 60 ]] || die "El PostgreSQL del clon no respondió a tiempo."
  sleep 2
done

if [[ "${SKIP_RESTORE}" -eq 0 ]]; then
  log "Restaurando base en el clon"
  clone_script ./scripts/backups/restore_db.sh "${BACKUP_SOURCE}" --target-db "${CLONE_DB_NAME}" --drop-existing --yes --mode docker
fi

log "Levantando servicios Django del clon"
clone_compose up -d web worker nginx

if [[ "${SKIP_RESTORE}" -eq 0 ]]; then
  log "Restaurando media en el clon"
  clone_script ./scripts/backups/restore_media.sh "${BACKUP_SOURCE}" --docker-live --yes
fi

log "Validando Django dentro del clon"
TRIES=0
until (
  clone_compose exec -T web python manage.py check
); do
  TRIES=$((TRIES + 1))
  [[ "${TRIES}" -lt 20 ]] || die "El servicio web del clon no pasó django check a tiempo."
  sleep 3
done

log "Clon paralelo listo."
log "Ruta: ${TARGET_DIR}"
log "URL: http://127.0.0.1:${CLONE_NGINX_PORT}"
