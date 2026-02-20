#!/usr/bin/env bash
set -euo pipefail

cd /app
mkdir -p /app/logs

wait_for_tcp() {
  local host="$1"
  local port="$2"
  local label="$3"
  local timeout="${4:-180}"
  local deadline=$((SECONDS + timeout))

  while (( SECONDS < deadline )); do
    if python - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

try:
    with socket.create_connection((host, port), timeout=2):
        pass
except OSError:
    sys.exit(1)

sys.exit(0)
PY
    then
      echo ">> ${label} disponible en ${host}:${port}"
      return 0
    fi
    sleep 2
  done

  echo ">> Error: timeout esperando ${label} en ${host}:${port}" >&2
  return 1
}

wait_for_tcp "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}" "PostgreSQL"
wait_for_tcp "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" "Redis"

echo ">> Iniciando loop de worker..."
while true; do
  if ! python manage.py schedule_async_jobs --limit "${WORKER_SCHEDULE_LIMIT:-100}"; then
    echo ">> Aviso: schedule_async_jobs falló en este ciclo." >&2
  fi

  if ! python manage.py run_async_jobs --limit "${WORKER_RUN_LIMIT:-50}" --worker-name "${WORKER_NAME:-docker-worker}"; then
    echo ">> Aviso: run_async_jobs falló en este ciclo." >&2
  fi

  sleep "${WORKER_POLL_SECONDS:-10}"
done
