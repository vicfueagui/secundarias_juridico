#!/usr/bin/env bash
set -euo pipefail

cd /app
mkdir -p /app/logs /app/media /app/staticfiles

wait_for_postgres() {
  local host="${POSTGRES_HOST:-db}"
  local port="${POSTGRES_PORT:-5432}"
  local retries="${DB_WAIT_RETRIES:-60}"
  local sleep_seconds="${DB_WAIT_SLEEP_SECONDS:-2}"
  local attempt=1

  echo ">> Esperando PostgreSQL en ${host}:${port}..."
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
      echo ">> PostgreSQL disponible."
      return 0
    fi

    sleep "${sleep_seconds}"
    attempt=$((attempt + 1))
  done

  echo ">> Error: no se pudo conectar a PostgreSQL a tiempo." >&2
  return 1
}

wait_for_postgres

echo ">> Ejecutando migraciones..."
python manage.py migrate --noinput

echo ">> Ejecutando collectstatic..."
python manage.py collectstatic --noinput

echo ">> Iniciando Gunicorn en 0.0.0.0:8000..."
exec gunicorn asesores_especializados.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
