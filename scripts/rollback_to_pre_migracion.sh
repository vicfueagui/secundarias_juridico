#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker/docker-compose.yml"

ROLLBACK_TAG="pre-migracion-docker-2026-02-19"
DUMP_FILE=""
MEDIA_ARCHIVE=""
EXECUTE=0
ALLOW_DIRTY=0

usage() {
  cat <<'EOF'
Uso:
  ./scripts/rollback_to_pre_migracion.sh --dump <db.dump> --media <media.tar.gz> [opciones]

Opciones:
  --tag <tag>       Tag a restaurar (default: pre-migracion-docker-2026-02-19)
  --dump <archivo>  Dump PostgreSQL en formato custom (pg_dump -Fc)
  --media <archivo> Backup media .tar.gz
  --execute         Ejecuta rollback real (sin esto: dry-run)
  --allow-dirty     Permite working tree con cambios
  -h, --help        Muestra esta ayuda

Comportamiento:
  - Por defecto solo imprime pasos (dry-run).
  - Con --execute:
    1) Guarda snapshot local de la rama actual.
    2) Cambia al tag de rollback.
    3) Levanta DB del tag anterior.
    4) Restaura dump.
    5) Restaura media.
    6) Levanta servicios de la versión anterior.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      ROLLBACK_TAG="${2:-}"
      shift 2
      ;;
    --dump)
      DUMP_FILE="${2:-}"
      shift 2
      ;;
    --media)
      MEDIA_ARCHIVE="${2:-}"
      shift 2
      ;;
    --execute)
      EXECUTE=1
      shift
      ;;
    --allow-dirty)
      ALLOW_DIRTY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Parámetro no reconocido: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${DUMP_FILE}" || -z "${MEDIA_ARCHIVE}" ]]; then
  echo "Error: debes indicar --dump y --media." >&2
  usage
  exit 2
fi

if [[ ! -f "${DUMP_FILE}" ]]; then
  echo "Error: dump no encontrado: ${DUMP_FILE}" >&2
  exit 1
fi

if [[ ! -f "${MEDIA_ARCHIVE}" ]]; then
  echo "Error: backup media no encontrado: ${MEDIA_ARCHIVE}" >&2
  exit 1
fi

cd "${ROOT_DIR}"

if [[ "${ALLOW_DIRTY}" -ne 1 ]] && [[ -n "$(git status --porcelain)" ]]; then
  echo "Error: working tree no está limpio. Commit/stash antes de rollback o usa --allow-dirty." >&2
  exit 1
fi

if ! git rev-parse --verify "${ROLLBACK_TAG}" >/dev/null 2>&1; then
  echo "Error: tag no encontrado localmente: ${ROLLBACK_TAG}" >&2
  exit 1
fi

CURRENT_REF="$(git rev-parse --abbrev-ref HEAD)"
CURRENT_SHA="$(git rev-parse HEAD)"
SNAPSHOT_BRANCH="rollback_snapshot_$(date +%Y%m%d_%H%M%S)"

run_cmd() {
  local cmd="$1"
  if [[ "${EXECUTE}" -eq 1 ]]; then
    echo "+ ${cmd}"
    eval "${cmd}"
  else
    echo "+ ${cmd}"
  fi
}

echo "=== Plan de rollback ==="
echo "Tag objetivo: ${ROLLBACK_TAG}"
echo "Dump: ${DUMP_FILE}"
echo "Media: ${MEDIA_ARCHIVE}"
echo "Ref actual: ${CURRENT_REF} (${CURRENT_SHA})"
echo "Snapshot a crear: ${SNAPSHOT_BRANCH}"
echo "Modo: $([[ ${EXECUTE} -eq 1 ]] && echo 'EJECUCIÓN REAL' || echo 'DRY-RUN')"
echo

run_cmd "git branch ${SNAPSHOT_BRANCH} ${CURRENT_SHA}"
run_cmd "git checkout ${ROLLBACK_TAG}"
run_cmd "docker compose -f ${COMPOSE_FILE} down --remove-orphans"

DB_SERVICE_CMD='docker compose -f '"${COMPOSE_FILE}"' config --services | (grep -x db || grep -x postgres) | head -n 1'
if [[ "${EXECUTE}" -eq 1 ]]; then
  DB_SERVICE="$(eval "${DB_SERVICE_CMD}")"
else
  DB_SERVICE="\$( ${DB_SERVICE_CMD} )"
fi
run_cmd "docker compose -f ${COMPOSE_FILE} up -d ${DB_SERVICE}"

# Restore DB sobre la base configurada en .env del tag anterior.
run_cmd "cat ${DUMP_FILE} | docker compose -f ${COMPOSE_FILE} exec -T ${DB_SERVICE} sh -lc 'export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"; pg_restore -U \"\${POSTGRES_USER}\" -d \"\${POSTGRES_DB}\" --clean --if-exists --no-owner --no-privileges'"

# Reemplaza media por el backup validado.
run_cmd "rm -rf ${ROOT_DIR}/media"
run_cmd "tar -xzf ${MEDIA_ARCHIVE} -C ${ROOT_DIR}"

run_cmd "docker compose -f ${COMPOSE_FILE} up -d --build"
run_cmd "docker compose -f ${COMPOSE_FILE} ps"

echo
echo "Rollback preparado."
echo "Para volver al estado previo de código:"
echo "  git checkout ${CURRENT_REF}"
echo "  # o la rama snapshot: ${SNAPSHOT_BRANCH}"
