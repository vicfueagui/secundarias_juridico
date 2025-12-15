#!/usr/bin/env bash
set -euo pipefail

# Inicializa datos mínimos para entornos local/QA:
# - Ejecuta migraciones
# - Importa catálogo de CCT

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".venv/bin/activate" ]; then
  echo "⚠️  Crea y activa el entorno virtual (.venv) antes de ejecutar este script."
  exit 1
fi

source .venv/bin/activate

CSV_PATH="${1:-cct_secundarias.csv}"

if [ ! -f "$CSV_PATH" ]; then
  echo "⚠️  No se encontró el archivo de catálogo en '$CSV_PATH'."
  echo "    Pasa la ruta explícita: ./scripts/bootstrap_data.sh /ruta/a/cct_secundarias.csv"
  exit 1
fi

python manage.py migrate --noinput
python manage.py import_ccts --path "$CSV_PATH"

echo "✅ Datos cargados. Catálogo de CCT importado desde '$CSV_PATH'."
