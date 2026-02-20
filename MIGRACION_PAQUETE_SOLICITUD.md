# Paquete de Solicitud de Migracion a Docker

Fecha: 2026-02-20  
Rama: `chore/prep-migracion-docker`  
Tag base rollback: `pre-migracion-docker-2026-02-19` (`e336b8f`)

## 1) Alcance

### Incluye
- Contenerizacion de Django con Gunicorn (`web`).
- PostgreSQL en contenedor (`db`).
- Redis en contenedor (`redis`).
- Worker de jobs de Django (`worker` con `schedule_async_jobs` + `run_async_jobs`).
- Nginx como reverse proxy (`nginx`) para `/`, `/static/` y `/media/`.
- Persistencia de datos:
  - `postgres_data` para base de datos.
  - `static_data` para estaticos.
  - `MEDIA_MOUNT_SOURCE` para media (transicion: `../media`; objetivo final: `media_data`).
- Scripts y evidencia de backup/restore.
- Script de rollback a baseline pre-migracion.

### No incluye
- Cambios funcionales de negocio.
- Refactor mayor de modulos.
- Cambios de framework de colas.
- Optimizacion avanzada de performance.
- TLS productivo.

## 2) Variables Requeridas (`.env.example`)

### Secretas (obligatorias en produccion)
- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`

### No secretas (operativas)
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `DB_PORT`
- `DJANGO_ENV`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `REDIS_URL`
- `NGINX_PORT`
- `NGINX_PORT_LEGACY`
- `DJANGO_COLLECTSTATIC`
- `GUNICORN_WORKERS`
- `GUNICORN_TIMEOUT`
- `WORKER_NAME`
- `WORKER_POLL_SECONDS`
- `WORKER_RUN_LIMIT`
- `WORKER_SCHEDULE_LIMIT`

### Opcionales para bootstrap
- `DJANGO_BOOTSTRAP_CCTS`
- `DJANGO_CCTS_PATH`
- `DJANGO_CREATE_SUPERUSER`
- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

### Variable de transicion media (recomendada en esta etapa)
- `MEDIA_MOUNT_SOURCE` (default operativo actual: `../media`)

Ejemplo de arranque con transicion media:

```bash
MEDIA_MOUNT_SOURCE=../media ./scripts/docker_up.sh
```

## 3) Procedimiento de Despliegue

### Precheck
```bash
git status
git rev-parse --abbrev-ref HEAD
```

Confirmar rama objetivo:
- `chore/prep-migracion-docker`

### Levantar stack
```bash
./scripts/docker_up.sh
```

### Verificar estado de servicios
```bash
docker compose -f docker/docker-compose.yml ps
```

Se espera `Up` para:
- `db`
- `redis`
- `web`
- `worker`
- `nginx`

### Verificaciones HTTP minimas
```bash
curl -I http://127.0.0.1:8000/accounts/login/
curl -I http://127.0.0.1:8000/static/
curl -I http://127.0.0.1:8000/media/
```

## 4) Procedimiento de Backup/Restore

### Backup (DB + media + manifest)
```bash
./scripts/backup_data.sh
```

Genera:
- `backups/db_<timestamp>.dump`
- `backups/media_<timestamp>.tar.gz`
- `backups/backup_<timestamp>.manifest`

### Validar restore en entorno aparte (obligatorio)
```bash
./scripts/validate_restore.sh \
  backups/db_<timestamp>.dump \
  backups/media_<timestamp>.tar.gz
```

Genera:
- `backups/restore_validation_<timestamp>.md`

Criterio de validez:
- Si no pasa `validate_restore.sh`, el backup NO es valido.

## 5) Checklist de Validacion (DoD operacional)

- [ ] `docker compose up -d --build` sin errores.
- [ ] `docker compose ps` con `db redis web worker nginx` arriba.
- [ ] Login/logout funcional.
- [ ] CRUD principal funcional (crear/listar/editar/eliminar).
- [ ] Adjuntos media suben y se visualizan.
- [ ] PDF se genera y descarga.
- [ ] Worker procesa al menos 1 job.
- [ ] `/static/` y `/media/` servidos por nginx.
- [ ] Reinicio de contenedores mantiene datos/media.
- [ ] Backup generado.
- [ ] Restore validado en entorno aparte.
- [ ] Sin errores criticos en logs (sin tracebacks durante smoke test).

### Ejecucion semiautomatica recomendada
```bash
SMOKE_EXPECTED_SERVICES="db redis web worker nginx" \
./smoke_test.sh --strict
```

## 6) Plan de Rollback

Script oficial:
- `scripts/rollback_to_pre_migracion.sh`

### Dry-run (recomendado antes de ejecutar)
```bash
./scripts/rollback_to_pre_migracion.sh \
  --dump backups/db_20260220_102204.dump \
  --media backups/media_20260220_102204.tar.gz
```

### Ejecucion real
```bash
./scripts/rollback_to_pre_migracion.sh \
  --dump backups/db_20260220_102204.dump \
  --media backups/media_20260220_102204.tar.gz \
  --execute
```

Resultado esperado:
- Checkout del tag `pre-migracion-docker-2026-02-19`.
- Restore de DB + media.
- Stack anterior levantado y operativo en menos de 30 minutos.

## 7) Evidencia a Entregar en Solicitud

- `docker compose -f docker/docker-compose.yml ps`
- Reporte de smoke test en `smoke_test_reports/`
- Manifest de backup en `backups/backup_<timestamp>.manifest`
- Reporte de validacion de restore en `backups/restore_validation_<timestamp>.md`
- Confirmacion de tag rollback disponible

## 8) Aprobacion

- Alcance aprobado: [ ] Si [ ] No  
- Variables revisadas: [ ] Si [ ] No  
- Despliegue aprobado: [ ] Si [ ] No  
- Backup/Restore aprobado: [ ] Si [ ] No  
- Rollback aprobado: [ ] Si [ ] No  
- Responsable de aprobacion: ____________________  
- Fecha: ____________________
