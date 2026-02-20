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
- `MEDIA_MOUNT_SOURCE` (default `../media`) -> `/app/media` (`web`/`worker`) y `/var/www/media` (`nginx`)
  - transición segura: evita 404 en adjuntos históricos existentes en host.
  - objetivo final: `MEDIA_MOUNT_SOURCE=media_data` para operar solo con volumen Docker.
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
- `nginx` sirve `/static/` y `/media/` desde montajes persistentes y proxea app a `web:8000`.
- `scripts/docker_up.sh` fuerza `MEDIA_MOUNT_SOURCE` para asegurar consistencia entre `web`, `worker` y `nginx`.
