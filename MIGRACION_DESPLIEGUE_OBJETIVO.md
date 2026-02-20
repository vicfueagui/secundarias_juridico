# Paso 6 - Diseño de Despliegue Objetivo

Fecha: 2026-02-20
Rama: chore/prep-migracion-docker

## Stack objetivo implementado en `docker/docker-compose.yml`

Servicios:

- `web` (Django + Gunicorn)
- `db` (PostgreSQL 15)
- `redis` (Redis 7)
- `worker` (procesamiento de jobs propios de Django)
- `nginx` (reverse proxy + static/media)

## Volúmenes persistentes

- `postgres_data` -> `/var/lib/postgresql/data` (servicio `db`)
- `media_data` -> `/app/media` (`web`/`worker`) y `/var/www/media` (`nginx`)
- `static_data` -> `/app/staticfiles` (`web`/`worker`) y `/var/www/static` (`nginx`)

## Healthchecks mínimos (requisito)

- `db`:
  - `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`
- `redis`:
  - `redis-cli ping`
- `web`:
  - probe HTTP interno a `/accounts/login/` en `127.0.0.1:8000`
- `nginx`:
  - probe HTTP interno a `/nginx-health`

## Notas operativas clave

- `web` ya arranca con Gunicorn (no `runserver`) en `docker/entrypoint.sh`.
- `web` ejecuta `migrate` y `collectstatic` al iniciar.
- `worker` usa comandos propios del proyecto:
  - `schedule_async_jobs`
  - `run_async_jobs`
- `nginx` sirve `/static/` y `/media/` desde volúmenes persistentes y proxea app a `web:8000`.
