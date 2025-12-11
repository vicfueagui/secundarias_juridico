#!/usr/bin/env python3
"""Utility script for Django administrative tasks."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "asesores_especializados.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - Django import guard
        raise ImportError(
            "No se pudo importar Django. Revisa si está instalado y disponible en tu entorno."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
