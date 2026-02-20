#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker/docker-compose.yml"

cd "${ROOT_DIR}"

if ! command -v docker >/dev/null 2>&1; then
  echo ">> Error: no se encontró el comando 'docker'. Instala/abre Docker Desktop y vuelve a intentar."
  exit 1
fi

port_in_use() {
  local port="$1"
  if ! command -v lsof >/dev/null 2>&1; then
    return 1
  fi
  lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
}

PRIMARY_NGINX_PORT="${NGINX_PORT:-8080}"
LEGACY_NGINX_PORT="${NGINX_PORT_LEGACY:-8000}"
MEDIA_SOURCE="${MEDIA_MOUNT_SOURCE:-../media}"

if [[ "${PRIMARY_NGINX_PORT}" == "${LEGACY_NGINX_PORT}" ]]; then
  echo ">> Error: NGINX_PORT y NGINX_PORT_LEGACY no pueden ser iguales."
  exit 1
fi

if port_in_use "${PRIMARY_NGINX_PORT}"; then
  echo ">> Aviso: el puerto ${PRIMARY_NGINX_PORT} ya está en uso. Si no es este stack, el arranque puede fallar."
fi

if port_in_use "${LEGACY_NGINX_PORT}"; then
  echo ">> Aviso: el puerto ${LEGACY_NGINX_PORT} ya está en uso. Si no es este stack, el arranque puede fallar."
fi

echo ">> Montaje de media activo: ${MEDIA_SOURCE}"

if [[ "${1:-}" == "--initdb" ]]; then
  echo ">> Levantando servicios base para inicialización (db + redis)..."
  docker compose -f "${COMPOSE_FILE}" up -d db redis
  echo ">> Ejecutando inicialización de base de datos (migrate)..."
  docker compose -f "${COMPOSE_FILE}" run --rm web /bin/bash -lc "python manage.py migrate --noinput"
fi

echo ">> Levantando stack Docker objetivo (db + redis + web + worker + nginx)..."
NGINX_PORT="${PRIMARY_NGINX_PORT}" NGINX_PORT_LEGACY="${LEGACY_NGINX_PORT}" MEDIA_MOUNT_SOURCE="${MEDIA_SOURCE}" \
  docker compose -f "${COMPOSE_FILE}" up -d --build db redis web worker nginx

echo ">> Servicios activos:"
docker compose -f "${COMPOSE_FILE}" ps

echo ""
echo "Sistema listo en:"
echo "  - http://127.0.0.1:${PRIMARY_NGINX_PORT}"
echo "  - http://127.0.0.1:${LEGACY_NGINX_PORT} (compatibilidad temporal)"
echo "Para ver logs en vivo: docker compose -f ${COMPOSE_FILE} logs -f web worker nginx"
