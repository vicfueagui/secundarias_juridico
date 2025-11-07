"""Configuración WSGI para el proyecto CEJEI Licencias."""
from __future__ import annotations

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cejei_licencias.settings")

application = get_wsgi_application()
