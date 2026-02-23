#!/usr/bin/env bash
set -euo pipefail

cd /app
mkdir -p /app/logs

wait_for_tcp() {
  local host="$1"
  local port="$2"
  local label="$3"
  local retries="${4:-60}"
  local sleep_seconds="${5:-2}"
  local attempt=1

  while (( attempt <= retries )); do
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
    sleep "${sleep_seconds}"
    attempt=$((attempt + 1))
  done

  echo ">> Error: timeout esperando ${label} en ${host}:${port}" >&2
  return 1
}

wait_for_tcp "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}" "PostgreSQL"
wait_for_tcp "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" "Redis"

echo ">> Iniciando loop de worker..."
while true; do
  python manage.py schedule_async_jobs --limit "${WORKER_SCHEDULE_LIMIT:-100}"
  python manage.py run_async_jobs --limit "${WORKER_RUN_LIMIT:-50}" --worker-name "${WORKER_NAME:-docker-worker}"
  sleep "${WORKER_SLEEP_SECONDS:-5}"
done
