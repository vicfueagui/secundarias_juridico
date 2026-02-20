# Paso 7 - Plan de Rollback (< 30 minutos)

Fecha: 2026-02-20
Rama actual: `chore/prep-migracion-docker`
Tag de retorno: `pre-migracion-docker-2026-02-19` (`e336b8f`)

## 1) Objetivo operativo

- Volver a la versión anterior funcional en menos de 30 minutos.
- Restaurar **código**, **base de datos** y **media**.
- Dejar servicios levantados y accesibles.

## 2) Artefactos obligatorios de entrada

- Dump DB validado:
  - `backups/db_20260220_102204.dump`
- Backup media validado:
  - `backups/media_20260220_102204.tar.gz`
- Evidencia de restore previo (validez del backup):
  - `backups/restore_validation_20260220_102313.md`

## 3) Script de ejecución

Script oficial:

- `scripts/rollback_to_pre_migracion.sh`

Modo seguro:

- Dry-run por defecto (no ejecuta cambios).
- Ejecución real solo con `--execute`.

## 4) Procedimiento exacto (ejecución real)

### 4.1 Precheck (2-5 min)

```bash
cd /Users/admin/Documents/project_secu_juridi
git fetch --tags
git status
```

Verificar que existen:

```bash
ls -lh backups/db_20260220_102204.dump backups/media_20260220_102204.tar.gz
```

### 4.2 Rollback automatizado (10-20 min)

```bash
./scripts/rollback_to_pre_migracion.sh \
  --dump backups/db_20260220_102204.dump \
  --media backups/media_20260220_102204.tar.gz \
  --execute
```

El script ejecuta exactamente:
1. Crea snapshot local del HEAD actual (`rollback_snapshot_<timestamp>`).
2. Cambia a `pre-migracion-docker-2026-02-19`.
3. Baja stack actual (`docker compose down --remove-orphans`).
4. Levanta DB de la versión anterior.
5. Restaura dump en `POSTGRES_DB` con `pg_restore --clean --if-exists`.
6. Restaura carpeta `media` desde tar.
7. Levanta la versión anterior (`docker compose up -d --build`).
8. Muestra estado de servicios (`docker compose ps`).

### 4.3 Verificación post-rollback (5 min)

```bash
docker compose -f docker/docker-compose.yml ps
curl -I http://127.0.0.1:8000/
```

Validar en aplicación:
- login
- acceso a adjuntos históricos (media)
- operación base sin error crítico

## 5) Presupuesto de tiempo (RTO)

- Precheck: 2-5 min
- Ejecución rollback: 10-20 min
- Verificación final: 5 min
- **Total objetivo: 17-30 min**

## 6) Fallback manual (si script falla)

```bash
git checkout pre-migracion-docker-2026-02-19
docker compose -f docker/docker-compose.yml down --remove-orphans
docker compose -f docker/docker-compose.yml up -d postgres

cat backups/db_20260220_102204.dump | \
docker compose -f docker/docker-compose.yml exec -T postgres sh -lc \
'export PGPASSWORD="${POSTGRES_PASSWORD}";
 pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists --no-owner --no-privileges'

rm -rf media
tar -xzf backups/media_20260220_102204.tar.gz -C .

docker compose -f docker/docker-compose.yml up -d --build
docker compose -f docker/docker-compose.yml ps
```

## 7) Criterio de éxito del rollback

Rollback exitoso solo si:
- versión de código anterior levantada (`tag` objetivo),
- dump restaurado sin error,
- media restaurada,
- login y flujo base operativos.
