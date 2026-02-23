# README_DEPLOY - Dockerizacion Institucional

## 1) Auditoria tecnica final (resumen)
- Proyecto Django: `asesores_especializados`.
- Entrypoints detectados: `asesores_especializados/settings.py`, `asesores_especializados/wsgi.py`, `asesores_especializados/asgi.py`.
- Worker real del proyecto: comandos Django `schedule_async_jobs` y `run_async_jobs` (no Celery/RQ nativo).
- PDF: `WeasyPrint` en `requirements.txt`, por lo que se instalan librerias de sistema (`libpango`, `libpangocairo`, `libcairo2`, `shared-mime-info`).

## 2) Requisitos
- Docker Engine + Docker Compose Plugin (`docker compose`).
- Archivo `.env` creado desde `.env.example`.
- Puertos disponibles:
  - `8080` (principal)
  - `8000` (compatibilidad temporal)
  - `5532` (acceso host a PostgreSQL, opcional)

## 3) Estructura de despliegue
- `Dockerfile`
- `docker-compose.yml`
- `deploy/entrypoint.sh`
- `deploy/worker.sh`
- `deploy/nginx/default.conf`
- `scripts/backup.sh`
- `scripts/restore.sh`

## 4) Variables requeridas
Tomar base de `.env.example`.

Minimas:
- Django: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- DB: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- Redis/worker: `REDIS_URL`, `WORKER_SLEEP_SECONDS`
- Gunicorn: `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`

## 5) Levantar stack
```bash
docker compose up -d --build
```

Verificar servicios:
```bash
docker compose ps
```

Validacion de configuracion:
```bash
docker compose config
python manage.py check
```

## 6) Logs
```bash
docker compose logs -f web
docker compose logs -f worker
docker compose logs -f nginx
docker compose logs -f db
```

## 7) Superusuario (si aplica)
```bash
docker compose exec web python manage.py createsuperuser
```

## 8) Actualizacion de version
```bash
git pull
docker compose up -d --build
docker compose exec web python manage.py migrate --noinput
```

## 9) Backup y restore
Backup (DB + media):
```bash
./scripts/backup.sh
```

Restore (DB + media):
```bash
./scripts/restore.sh --dump backups/db_<timestamp>.dump --media backups/media_<timestamp>.tar.gz
```

Nota operativa:
- Si no se valida restore en entorno de prueba, el backup no se considera valido.

## 10) Checklist de validacion operativa
- `docker compose up -d --build` sin errores.
- `docker compose ps` con `db`, `redis`, `web`, `worker`, `nginx` en estado `Up`/`healthy`.
- Login y CRUD principal funcionales.
- Adjuntos y PDF funcionando por `/media/`.
- Worker ejecuta jobs sin errores criticos.
- `/static/` y `/media/` servidos por nginx.
- Backup y restore probados.

## 11) Rollback (resumen)
- Referencia de rollback: tag `pre-migracion-docker-2026-02-19`.
- Restaurar dump + media y levantar version anterior segun `MIGRACION_PLAN_ROLLBACK.md`.

## 12) Troubleshooting rapido
- `DisallowedHost`: agregar host/IP a `DJANGO_ALLOWED_HOSTS`.
- `403 CSRF`: agregar origen a `DJANGO_CSRF_TRUSTED_ORIGINS`.
- `404 /media`: revisar volumen `media_data` y existencia del archivo en `/app/media`.
- Web no levanta: revisar migraciones y `docker compose logs -f web`.
- Worker sin actividad: revisar `docker compose logs -f worker` y valores `WORKER_*`.
