# Restauración Total Paso a Paso

Guía operativa simple para volver a levantar `project_secu_juridi` desde un respaldo formal, sin improvisar.

## 1. Escenario recomendado

Restaurar primero en carpeta alterna para no tocar la instalación estable.

Carpeta sugerida:

```text
../project_secu_juridi_restore
```

## 2. Respaldo base a usar

Puedes usar `backups/latest` o una corrida concreta.

Ejemplo validado:

- [`backups/latest`](/Users/admin/Documents/project_secu_juridi/backups/latest)

## 3. Restaurar código y configuración

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/restore_code.sh backups/latest --target-dir ../project_secu_juridi_restore
./scripts/backups/restore_env.sh backups/latest --target-file ../project_secu_juridi_restore/.env --yes
```

## 4. Ajustar puertos si el original sigue corriendo

Si el proyecto original sigue levantado en `8000/8080`, cambia en `../project_secu_juridi_restore/.env`:

```env
NGINX_PORT=8082
NGINX_PORT_LEGACY=8002
POSTGRES_PORT=5543
COMPOSE_PROJECT_NAME=project_secu_juridi_restore
```

## 5. Levantar el stack restaurado

```bash
cd ../project_secu_juridi_restore
docker compose up -d --build db redis
```

## 6. Restaurar base y media

```bash
cd ../project_secu_juridi_restore
./scripts/backups/restore_db.sh /Users/admin/Documents/project_secu_juridi/backups/latest --target-db cejei_licencias_restore --drop-existing --yes --mode docker
docker compose up -d web worker nginx
./scripts/backups/restore_media.sh /Users/admin/Documents/project_secu_juridi/backups/latest --docker-live --yes
```

Nota:

- el modo `direct` de los scripts ya selecciona automáticamente un cliente PostgreSQL compatible si tienes más de uno instalado en macOS

## 7. Validar que quedó bien

```bash
cd ../project_secu_juridi_restore
docker compose exec -T web python manage.py check
docker compose ps
```

Luego abre la URL configurada en `.env`.

## 8. Alternativa más segura para evolución

Si tu objetivo no es una restauración desde archive sino una copia operativa del estado actual, usa:

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/prepare_parallel_clone.sh --target-dir ../project_secu_juridi_dev
```

Ese flujo:

- crea el clon
- ajusta `.env`
- publica PostgreSQL del clon en un puerto propio
- levanta el stack del clon
- restaura base y media
- deja el clon listo para empezar a trabajar
