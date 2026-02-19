# Paso 3 - Inventario Técnico Real

Fecha: 2026-02-19
Rama: chore/prep-migracion-docker

## 1) Módulo Django real (settings.py / wsgi.py)

- Módulo de configuración: `asesores_especializados.settings` (`asesores_especializados/settings.py`).
- Módulo WSGI: `asesores_especializados.wsgi.application` (`asesores_especializados/settings.py:87` y `asesores_especializados/wsgi.py:13-15`).
- Módulo ASGI declarado: `asesores_especializados.asgi.application` (`asesores_especializados/settings.py:88`).
- `wsgi.py` carga variables desde `.env` con `python-dotenv` (`asesores_especializados/wsgi.py:8-11`).
- Estado actual de ejecución en Docker:
  - El contenedor `web` arranca con `python manage.py runserver 0.0.0.0:8000` (`docker/entrypoint.sh:59-60`).
  - Aún no está configurado Gunicorn en runtime.

## 2) Dependencias Python (inventario real)

Archivo principal: `requirements.txt`.

- Framework/API:
  - `Django>=4.2,<5.0`
  - `djangorestframework>=3.14`
  - `djangorestframework-simplejwt>=5.3`
  - `django-filter>=23.0`
  - `django-simple-history>=3.4`
- Base de datos:
  - `psycopg2-binary>=2.9`
- Utilidades:
  - `python-dateutil>=2.8`
  - `python-dotenv>=1.0`
  - `pandas>=2.0`
  - `Pillow>=10.0`
- PDF:
  - `WeasyPrint>=61.0`

Archivo secundario: `reporte_plantilla_licencias/requirements.txt`:
- `jinja2`
- `weasyprint`
- `pandas`

## 3) Dependencias de sistema operativo (PDF/OCR)

Definidas en `Dockerfile` (`Dockerfile:9-19`):

- Compilación/base:
  - `build-essential`, `gcc`, `libffi-dev`, `libpq-dev`
- PDF/WeasyPrint:
  - `libcairo2`, `libpango-1.0-0`, `libpangocairo-1.0-0`, `shared-mime-info`

Hallazgo OCR:
- No se encontraron dependencias OCR (por ejemplo `tesseract`, `pytesseract`, `ocrmypdf`, `poppler`) en Dockerfile ni requirements.
- Conclusión: hoy hay soporte de generación/render de PDF, no pipeline OCR explícito.

## 4) Tipo de worker real (Celery/RQ/comando propio)

Tipo real identificado: **comando propio + cola en base de datos** (sin Celery/RQ).

Evidencia:
- Comando para procesar cola: `run_async_jobs` (`tramites/management/commands/run_async_jobs.py:8-23`).
- Comando para encolar programados: `schedule_async_jobs` (`tramites/management/commands/schedule_async_jobs.py:8-17`).
- Infraestructura de handlers en código:
  - Registro de handlers en memoria `JOB_HANDLERS` (`tramites/services/jobs.py:16-25`).
  - Ejecución de cola pendiente (`tramites/services/jobs.py:230-237`).
  - Handlers implementados: `data_quality_scan`, `healthcheck`, `sla_alert_scan` (`tramites/services/jobs.py:240-261`).
- Persistencia de cola en modelos:
  - `ScheduledJob` y `AsyncJob` (`tramites/models.py:1676-1762`).

Estado actual de compose:
- `docker/docker-compose.yml` no define servicio `worker` dedicado (solo `postgres`, `web`, `initdb`).

## 5) Rutas reales de STATIC/MEDIA y base de datos actual

### 5.1 Configuración declarada

En settings:
- `STATIC_URL = "/static/"` (`asesores_especializados/settings.py:109`)
- `STATIC_ROOT = BASE_DIR / "staticfiles"` (`asesores_especializados/settings.py:110`)
- `MEDIA_URL = "/media/"` (`asesores_especializados/settings.py:113`)
- `MEDIA_ROOT = BASE_DIR / "media"` (`asesores_especializados/settings.py:114`)
- `DATABASES["default"]` usa PostgreSQL y variables `POSTGRES_*` (`asesores_especializados/settings.py:91-99`).

### 5.2 Valores efectivos en ejecución (contenedor `web`)

Verificado con `docker compose exec web python manage.py shell`:

- `ENGINE=django.db.backends.postgresql`
- `NAME=cejei_licencias`
- `USER=cejei`
- `HOST=postgres`
- `PORT=5432`
- `STATIC_ROOT=/app/staticfiles`
- `MEDIA_ROOT=/app/media`
- `STATIC_URL=/static/`
- `MEDIA_URL=/media/`

### 5.3 Contexto local fuera de contenedor

En `.env` del repo:
- `POSTGRES_HOST=127.0.0.1`
- `POSTGRES_PORT=5532`

Conclusión:
- Dentro de Docker, Django resuelve DB en `postgres:5432`.
- Desde host local (sin red interna compose), el acceso es por `127.0.0.1:5532`.

## 6) Brechas detectadas para la migración objetivo

- El alcance objetivo del Paso 2 pide `web` con Gunicorn y servicios `redis/worker/nginx`; actualmente:
  - `web` usa `runserver`.
  - No existe servicio `redis`.
  - No existe servicio `worker`.
  - No existe servicio `nginx`.
- No hay dependencias OCR instaladas; si OCR es requisito real, debe incorporarse explícitamente.

## 7) Estado del Paso 3

- Inventario técnico real: **completado**.
- Fuente de verdad: código actual + runtime en contenedor.
