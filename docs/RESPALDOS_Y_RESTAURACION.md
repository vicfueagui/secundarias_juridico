# Respaldos y Restauración

Documento operativo para blindar `project_secu_juridi` sin tocar la lógica de negocio ni romper la compatibilidad histórica de `tramites` con `app_label = "licencias"`.

Si esta práctica la vas a repetir, usa también el tablero de seguimiento:

- [KANBAN_PERSONAL_BLINDAJE_OPERATIVO.md](/Users/admin/Documents/project_secu_juridi/docs/KANBAN_PERSONAL_BLINDAJE_OPERATIVO.md)

## 1. Qué deja resuelto esta capa

- respaldo formal de base de datos PostgreSQL
- respaldo formal de `media`
- respaldo formal del código fuente
- verificación básica de restaurabilidad
- restauración segura a base alterna o carpeta alterna
- evidencia mínima en `manifest.env`, `checksums.sha256` y reporte de verificación

## 2. Scripts oficiales

Ubicación: [`scripts/backups/`](/Users/admin/Documents/project_secu_juridi/scripts/backups)

- [`backup_db.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/backup_db.sh)
- [`backup_media.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/backup_media.sh)
- [`backup_code.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/backup_code.sh)
- [`backup_env.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/backup_env.sh)
- [`backup_full.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/backup_full.sh)
- [`verify_backup.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/verify_backup.sh)
- [`restore_code.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/restore_code.sh)
- [`restore_env.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/restore_env.sh)
- [`restore_db.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/restore_db.sh)
- [`restore_media.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/restore_media.sh)
- [`clone_worktree.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/clone_worktree.sh)
- [`prepare_parallel_clone.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backups/prepare_parallel_clone.sh)

También hay atajos en [`Makefile`](/Users/admin/Documents/project_secu_juridi/Makefile):

- `make backup-db`
- `make backup-media`
- `make backup-code`
- `make backup-env`
- `make backup-full`
- `make verify-backup`
- `make clone-worktree`
- `make prepare-clone`
- `make restore-code`
- `make restore-env`

## 3. Dónde se guardan los respaldos

Patrón:

```text
backups/YYYY-MM-DD/project_secu_juridi_<entorno>_YYYYMMDD_HHMMSS/
```

Dentro de cada corrida se generan, según aplique:

- dump `.dump` de PostgreSQL
- archive `.tar.gz` de `media`
- archive `.tar.gz` del código fuente
- respaldo seguro de `.env`
- archivo redactado de llaves de entorno
- `git bundle`
- `manifest.env`
- `checksums.sha256`
- `git_status.txt`
- `git_diff.patch` si había cambios locales
- `backup_verification_*.md`

Además, `backups/latest` apunta al respaldo más reciente.

## 4. Camino recomendado hoy en este repo

Diagnóstico real del 2026-03-17:

- El stack validado hoy es [`docker-compose.yml`](/Users/admin/Documents/project_secu_juridi/docker-compose.yml) de la raíz.
- La base activa hoy sí responde por `docker compose exec`.
- La ruta local `127.0.0.1:5532` no respondió en esta revisión.
- `media/` del host y `/app/media` del contenedor activo no coinciden en conteo ni tamaño.

Conclusión práctica:

- usa `backup_full.sh` o `backup_db.sh` en modo `auto` o `docker`
- usa `backup_media.sh` en modo `auto` o `docker` mientras el stack raíz sea el activo
- usa `direct` solo cuando tu PostgreSQL realmente responda por `POSTGRES_HOST` y `POSTGRES_PORT`
- en modo `direct`, los scripts buscan automáticamente un cliente PostgreSQL compatible y priorizan la versión más nueva disponible

## 5. Comandos exactos

### Respaldo integral

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/backup_full.sh
```

O con `make`:

```bash
cd /Users/admin/Documents/project_secu_juridi
make backup-full
```

### Respaldo integral + verificación

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/backup_full.sh --verify
```

### Verificar el respaldo más reciente

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/verify_backup.sh
```

### Respaldar solo base

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/backup_db.sh --mode auto
```

### Respaldar solo media

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/backup_media.sh --mode auto
```

### Respaldar solo código

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/backup_code.sh
```

### Respaldar entorno sensible

Esto copia `.env` al respaldo local con permisos restringidos. No se sube a Git.

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/backup_env.sh
```

## 6. Restauración segura

### Restaurar código a una carpeta nueva

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/restore_code.sh backups/latest --target-dir ../project_secu_juridi_restore
```

### Restaurar `.env` a un archivo controlado

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/restore_env.sh backups/latest --target-file ../project_secu_juridi_restore/.env --yes
```

### Restaurar base a una base NUEVA

Esto es lo recomendado primero.

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/restore_db.sh backups/latest --target-db cejei_licencias_restore_20260317
```

### Restaurar base sobre la base activa

Solo cuando estés completamente seguro.

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/restore_db.sh backups/latest --target-db cejei_licencias --drop-existing --yes
```

### Restaurar media a una carpeta alterna en host

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/restore_media.sh backups/latest --target-dir backups/restored_media_manual_20260317
```

### Restaurar media sobre el contenedor activo

Esto reemplaza `/app/media` del `web` activo.

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/restore_media.sh backups/latest --docker-live --yes
```

## 7. Restauración total paso a paso

Para restaurar un proyecto completo en carpeta aparte, sin tocar el original:

1. Restaura el código.
2. Restaura el `.env`.
3. Ajusta puertos si no quieres chocar con el proyecto original.
4. Levanta Docker en la carpeta restaurada.
5. Restaura base de datos y `media`.

Comandos:

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/restore_code.sh backups/latest --target-dir ../project_secu_juridi_restore
./scripts/backups/restore_env.sh backups/latest --target-file ../project_secu_juridi_restore/.env --yes

cd ../project_secu_juridi_restore
docker compose up -d --build db redis
./scripts/backups/restore_db.sh /Users/admin/Documents/project_secu_juridi/backups/latest --target-db cejei_licencias_restore --drop-existing --yes --mode docker
docker compose up -d web worker nginx
./scripts/backups/restore_media.sh /Users/admin/Documents/project_secu_juridi/backups/latest --docker-live --yes
docker compose exec -T web python manage.py check
```

## 8. Qué valida `verify_backup.sh`

- que los archivos listados en `checksums.sha256` sigan íntegros
- que el dump sea legible por `pg_restore --list`
- que el dump se pueda restaurar a una base temporal
- que el conteo de tablas y de `django_migrations` coincida contra el origen vivo
- que `media` se pueda extraer
- que el conteo de archivos de `media` coincida con el origen vivo cuando ese origen sea alcanzable
- que el respaldo de código sea legible y contenga `manage.py`
- que el `git bundle` sea verificable si existe
- que exista respaldo de entorno y archivo redactado si aplica

## 9. Evidencia validada en este repo

Corrida real validada en este entorno:

```text
backups/2026-03-17/project_secu_juridi_development_20260317_130526
```

Resultados observados:

- base origen/restaurada: `72` tablas públicas
- `django_migrations` origen/restaurada: `83`
- media origen/restaurada: `512` archivos
- respaldo de código: `OK`
- respaldo de entorno: `OK`
- `git bundle`: `OK`
- clon paralelo validado en `http://127.0.0.1:8081`
- modo directo validado contra `127.0.0.1:5542` con cliente PostgreSQL compatible

Reporte:

- [`backup_verification_20260317_130526.md`](/Users/admin/Documents/project_secu_juridi/backups/2026-03-17/project_secu_juridi_development_20260317_130526/backup_verification_20260317_130526.md)

## 10. Notas importantes

- El respaldo de código excluye `.venv`, `backups`, `media`, `staticfiles`, `node_modules`, `*.dump`, `*.tar.gz` y temporales pesados.
- El respaldo de código excluye `.env`, pero `backup_env.sh` lo resguarda por separado dentro del respaldo local con permisos restringidos.
- La app sigue siendo `tramites`, pero la compatibilidad histórica depende de `licencias`; no cambies eso en esta fase.
- El flujo de importación base del catálogo CCT sigue siendo:

```bash
python manage.py import_ccts --path "cct_secundarias.csv"
```

- Si `verify_backup.sh` no puede validar modo `direct`, revisa primero que `POSTGRES_HOST` y `POSTGRES_PORT` realmente respondan.
