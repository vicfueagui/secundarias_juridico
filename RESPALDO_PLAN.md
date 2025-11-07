# Plan maestro de respaldos – CEJEI Licencias

Guía operativa para reproducir manualmente respaldos seguros del proyecto ubicado en `/Users/admin/Documents/project_secu_juridi`. El objetivo es que cualquier miembro pueda ejecutar o auditar el proceso sin depender de memoria institucional.

---

## 1. Alcance e inventario crítico
- **Código y dependencias**: repositorio Git, `requirements.txt`, `tailwind.config.js`, scripts utilitarios y configuración de Docker.
- **Base de datos**: PostgreSQL (`cejei_licencias`, usuario `cejei`, host configurable vía variables `POSTGRES_*`).
- **Archivos generados**: `staticfiles/` (builds) y `media/` (subidas por usuarios). Incluir bitácoras relevantes (`django_server.log`) solo si son requeridas para auditorías.
- **Credenciales y llaves**: `.env`, secretos JWT, claves de despliegue. No se almacenan en texto plano dentro del backup; se guardan cifrados aparte.

---

## 2. Buenas prácticas mínimas
1. **Regla 3-2-1**: 3 copias, 2 medios distintos, 1 fuera del sitio (ej. nube cifrada).
2. **Integridad y trazabilidad**: generar `SHA256` para cada artefacto y registrar fecha/operador.
3. **Cifrado en reposo y tránsito**: usar `gpg` (asimétrico) o `age` antes de subir a destinos externos.
4. **Automatizar, pero ensayar manualmente**: al menos 1 restauración de prueba por sprint o mes.
5. **Rotación**: diarios incrementales (archivos modificados), semanales completos, retención mínima 30 días para completos y 7 días para incrementales.

---

## 3. Tablero Kanban + GTP (Goal / Task / Procedure)

| Kanban | Goal (Meta) | Task (Actividad) | Procedure (Pasos/Comandos) | Evidencia |
| --- | --- | --- | --- | --- |
| Backlog | Inventario actualizado | Auditar qué se debe respaldar | Revisar `RESPALDO_PLAN.md` y validar rutas vivas (`rg --files`, `ls media`). | Registro en `CONTROL DE PROTOCOLO.csv`. |
| Backlog | Ambiente listo | Verificar herramientas | Confirmar `pg_dump`, `tar`, `gpg`, `shasum` (`which pg_dump`). | Captura de comandos. |
| To Do | Congelar configuraciones | Exportar variables sensibles | `cp .env backups_seguros/.env.$(date +%Y%m%d)` → cifrar `gpg -c ...`. | Hash + ubicación segura. |
| To Do | Minimizar cambios | Pausar escritura | Opcional: colocar sitio en mantenimiento o bloquear conexiones de escritura. | Bitácora en `CONTROL DE PROTOCOLO.csv`. |
| Doing | Backup DB | `pg_dump` consistente | `PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER cejei_licencias > $BACKUP/db.sql`. | Tamaño + hash. |
| Doing | Backup código | Empaquetar repo limpio | `git status -sb` (asegurar limpio) → `tar -czf $BACKUP/code.tar.gz --exclude='.venv' --exclude='media' --exclude='staticfiles' project_secu_juridi`. | Hash `SHA256`. |
| Doing | Backup media/static | Copia incremental | `rsync -a --delete media $BACKUP/media/` y `rsync -a staticfiles $BACKUP/staticfiles/`. | Log rsync guardado. |
| Doing | Validar | Comprobar integridad | `find $BACKUP -type f -exec shasum -a 256 {} \; > $BACKUP/checksums.txt`. | Verificar contra restauración. |
| Doing | Off-site | Subir copia cifrada | `tar -cz $BACKUP | gpg -se -r <KEY> | rclone copy - remoto:cejei/licencias/`. | ID de carga. |
| Done | Prueba de restauración | Ensayar recuperación | Restaurar en entorno aislado: recrear DB con `psql -f db.sql`, levantar `python manage.py check`. | Checklist firmado. |
| Done | Documentar | Cierre del ciclo | Registrar fecha, operador, ubicación y resultados en `RESPALDO_PLAN.md` (sección bitácora) o hoja control. | Actualización confirmada. |

---

## 4. Procedimiento manual detallado

> Variables sugeridas para cada sesión
```bash
export PROJECT_ROOT="/Users/admin/Documents/project_secu_juridi"
export BACKUP_ROOT="$HOME/backups/cejei/licencias/$(date +%Y%m%d-%H%M)"
export POSTGRES_HOST=127.0.0.1
export POSTGRES_USER=cejei
export POSTGRES_DB=cejei_licencias
export BACKUP_TMP="$BACKUP_ROOT/tmp"
mkdir -p "$BACKUP_TMP"
```

### 4.1 Preparación
1. `cd $PROJECT_ROOT`.
2. `git status -sb` → evitar cambios no versionados (registrarlos aparte si existen).
3. Respaldar archivo `.env` y cualquier `secrets.json` usando cifrado simétrico: `gpg -c --output $BACKUP_ROOT/.env.gpg .env`.
4. Verificar espacio disponible: `df -h $BACKUP_ROOT`.

### 4.2 Exportar base de datos PostgreSQL
```bash
PGPASSWORD="$POSTGRES_PASSWORD" \
pg_dump --format=custom \
  --file "$BACKUP_ROOT/db-cejei-$(date +%Y%m%d-%H%M).dump" \
  --host "$POSTGRES_HOST" \
  --username "$POSTGRES_USER" \
  "$POSTGRES_DB"
```
- Guardar log `pg_dump` en `logs/backup-$(date).log`.
- Opcional: comprimir `gzip` si el dump es grande.

### 4.3 Empaquetar código y configuraciones
```bash
tar --exclude='.venv' \
    --exclude='media' \
    --exclude='staticfiles' \
    -czf "$BACKUP_ROOT/codebase-$(date +%Y%m%d-%H%M).tar.gz" \
    -C "$(dirname "$PROJECT_ROOT")" "$(basename "$PROJECT_ROOT")"
```
- Incluye migraciones, scripts de despliegue y carpetas `docker/`, `licencias/`, `tests/`.

### 4.4 Respaldar archivos estáticos y media
```bash
rsync -a --delete "$PROJECT_ROOT/staticfiles/" "$BACKUP_ROOT/staticfiles/"
rsync -a --delete "$PROJECT_ROOT/media/" "$BACKUP_ROOT/media/"
```
- Mantener histórico semanal completo y diarios incrementales (`rsync --link-dest` puede reducir espacio).

### 4.5 Verificación e integridad
```bash
find "$BACKUP_ROOT" -maxdepth 1 -type f -print0 | \
  xargs -0 shasum -a 256 > "$BACKUP_ROOT/checksums.txt"
```
- Documentar resultado y tamaño total (`du -sh "$BACKUP_ROOT"`).

### 4.6 Cifrado y replicación fuera del sitio
1. `tar -czf "$BACKUP_ROOT/full.tar.gz" -C "$BACKUP_ROOT" .`
2. `gpg --encrypt --recipient <LLAVE_PUBLICA> "$BACKUP_ROOT/full.tar.gz"`
3. Subir a almacenamiento externo (ej. `rclone copy "$BACKUP_ROOT/full.tar.gz.gpg" remoto:cejei/licencias/`).

### 4.7 Ensayo de restauración
1. Crear entorno limpio: `python -m venv .venv_restore && source .venv_restore/bin/activate`.
2. Restaurar DB: `pg_restore --clean --dbname=$POSTGRES_DB_TEST --host=localhost --username=cejei`.
3. Descomprimir código en carpeta temporal, instalar dependencias `pip install -r requirements.txt`, ejecutar `python manage.py check`.
4. Registrar incidencias y duración.

---

## 5. Calendario sugerido
- **Diario (nocturno)**: dump incremental de DB + rsync de `media/`.
- **Semanal (domingo)**: backup completo (DB + código + staticfiles + media), replicado off-site.
- **Mensual**: prueba de restauración + rotación de llaves GPG si aplica.

---

## 6. Bitácora resumida

| Fecha | Operador | Tipo de backup | Ubicación local | Ubicación off-site | Verificación | Observaciones |
| --- | --- | --- | --- | --- | --- | --- |
| _yyyy-mm-dd_ | _Nombre_ | Completo / Incremental | `/Users/.../backups/...` | `remoto:cejei/licencias/...` | ✅/⚠️ | _Notas_ |

Rellena esta sección tras cada ejecución para mantener la trazabilidad.

---

## 7. Checklist rápido antes de cerrar
- [ ] Hashes generados y almacenados.
- [ ] Archivos sensibles cifrados.
- [ ] Copia externa confirmada.
- [ ] Bitácora actualizada.
- [ ] Última restauración documentada hace ≤30 días (si no, programarla).
