#!/usr/bin/env bash
set -euo pipefail

cd /app
mkdir -p /app/logs

echo ">> Esperando PostgreSQL en ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
python - <<'PY'
import os
import socket
import sys
import time

host = os.getenv("POSTGRES_HOST", "postgres")
port = int(os.getenv("POSTGRES_PORT", "5432"))
deadline = time.time() + 180

while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(">> PostgreSQL disponible.")
            sys.exit(0)
    except OSError:
        time.sleep(2)

print(">> Error: no se pudo conectar a PostgreSQL a tiempo.", file=sys.stderr)
sys.exit(1)
PY

echo ">> Ejecutando migraciones..."
python manage.py migrate --noinput

if [[ "${DJANGO_COLLECTSTATIC:-true}" == "true" ]]; then
  echo ">> Ejecutando collectstatic..."
  python manage.py collectstatic --noinput
fi

if [[ "${DJANGO_BOOTSTRAP_CCTS:-false}" == "true" ]]; then
  CCTS_PATH="${DJANGO_CCTS_PATH:-cct_secundarias.csv}"
  if [[ -f "$CCTS_PATH" ]]; then
    echo ">> Importando catálogo CCT desde ${CCTS_PATH}..."
    python manage.py import_ccts --path "$CCTS_PATH"
  else
    echo ">> Aviso: DJANGO_BOOTSTRAP_CCTS=true pero no existe ${CCTS_PATH}. Se omite importación."
  fi
fi

if [[ "${DJANGO_CREATE_SUPERUSER:-false}" == "true" ]]; then
  echo ">> Verificando superusuario..."
  python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superusuario {username} creado.')
else:
    print(f'Superusuario {username} ya existe.')
"
fi

echo ">> Iniciando Gunicorn en 0.0.0.0:8000..."
exec gunicorn asesores_especializados.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
