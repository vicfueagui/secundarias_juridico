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

resolve_web_port() {
  if [[ -n "${WEB_PORT:-}" ]]; then
    if port_in_use "${WEB_PORT}"; then
      echo ">> Error: el puerto WEB_PORT=${WEB_PORT} ya está ocupado. Libéralo o usa otro puerto."
      exit 1
    fi
    echo "${WEB_PORT}"
    return 0
  fi

  local candidate="8000"
  if ! port_in_use "${candidate}"; then
    echo "${candidate}"
    return 0
  fi

  for candidate in 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010; do
    if ! port_in_use "${candidate}"; then
      echo "${candidate}"
      return 0
    fi
  done

  echo ">> Error: no hay puertos libres entre 8000 y 8010."
  exit 1
}

RESOLVED_WEB_PORT="$(resolve_web_port)"

if [[ -z "${WEB_PORT:-}" && "${RESOLVED_WEB_PORT}" != "8000" ]]; then
  echo ">> Aviso: el puerto 8000 está ocupado. Se usará ${RESOLVED_WEB_PORT} para Django."
fi

if [[ "${1:-}" == "--initdb" ]]; then
  echo ">> Levantando PostgreSQL para inicialización..."
  docker compose -f "${COMPOSE_FILE}" up -d postgres
  echo ">> Ejecutando inicialización de base de datos (migrate + import_ccts)..."
  docker compose -f "${COMPOSE_FILE}" run --rm initdb
fi

echo ">> Levantando servicios Docker (postgres + web)..."
WEB_PORT="${RESOLVED_WEB_PORT}" docker compose -f "${COMPOSE_FILE}" up -d --build postgres web

echo ">> Servicios activos:"
docker compose -f "${COMPOSE_FILE}" ps

echo ""
echo "Sistema listo en: http://127.0.0.1:${RESOLVED_WEB_PORT}"
echo "Para ver logs en vivo: docker compose -f ${COMPOSE_FILE} logs -f web"
