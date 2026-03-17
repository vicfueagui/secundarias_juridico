# Diagnóstico Inicial de Blindaje

Fecha del diagnóstico: 2026-03-17

## 1. Resumen ejecutivo

El repositorio `project_secu_juridi` ya no debe tratarse como experimento. Hoy funciona como activo institucional con operación real, adjuntos en `media`, historial de cambios, permisos sobre `licencias.*` y dependencias activas en PostgreSQL y Docker.

La tarea de blindaje debe ser conservadora. No procede renombrar la app, no procede tocar `app_label = "licencias"`, no procede alterar migraciones ni rutas actuales.

## 2. Hallazgos confirmados en el repo real

- Sí existe `manage.py` en la raíz del proyecto.
- Los settings activos son [`asesores_especializados/settings.py`](/Users/admin/Documents/project_secu_juridi/asesores_especializados/settings.py).
- La app principal es `tramites`, pero conserva `label = "licencias"` en [`tramites/apps.py`](/Users/admin/Documents/project_secu_juridi/tramites/apps.py).
- Sí existen `.env`, `.env.example`, `.venv`, `.git`, `docker-compose.yml`, `docker/docker-compose.yml`, `media/`, `staticfiles/` y `backups/`.
- No existe `Makefile` al momento del diagnóstico.
- El proyecto usa Python 3.11 y `python manage.py check` pasa sin errores en `.venv`.
- El proyecto usa PostgreSQL vía variables `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`.
- Los settings usan `django.db.backends.postgresql`.
- `MEDIA_ROOT` está parametrizado por `DJANGO_MEDIA_ROOT` y por defecto apunta a `/app/media`.
- `STATIC_ROOT` está parametrizado por `DJANGO_STATIC_ROOT` y por defecto apunta a `/app/staticfiles`.
- Sí existen scripts previos de respaldo/restauración en `scripts/`, pero están fragmentados y priorizan Docker.

## 3. Estado operativo detectado hoy

### Stack activo

- El stack activo hoy es el de [`docker-compose.yml`](/Users/admin/Documents/project_secu_juridi/docker-compose.yml) en la raíz.
- `db`, `web`, `worker` y `redis` están arriba.
- `nginx` está arriba pero con healthcheck marcado como `unhealthy`.
- El compose legado [`docker/docker-compose.yml`](/Users/admin/Documents/project_secu_juridi/docker/docker-compose.yml) existe, pero no está corriendo.

### Base de datos

- La base activa accesible hoy es la del contenedor `db` del compose raíz.
- Se confirmó acceso por `docker compose exec`.
- Conteos observados al momento del diagnóstico:
  - tablas públicas: `72`
  - registros en `django_migrations`: `83`
- La ruta de acceso local por `127.0.0.1:5532` no respondió en este entorno durante el diagnóstico.
- Conclusión práctica:
  - hoy el camino confiable de respaldo/restauración es `docker compose exec ...`
  - el camino por `pg_dump` directo debe quedar soportado, pero no quedó validado en este ambiente concreto

### Archivos adjuntos / media

- Sí existen adjuntos reales y el respaldo de `media` es obligatorio.
- Conteo en carpeta host `media/`: `418` archivos, tamaño aproximado `1.2G`.
- Conteo en `/app/media` del contenedor `web`: `512` archivos, tamaño aproximado `1.5G`.
- Esto confirma una diferencia entre la carpeta local y lo que hoy usa la app dentro del stack activo.
- Riesgo operativo:
  - respaldar solo `./media` puede dejar fuera archivos reales del volumen Docker actual

### Git

- El repositorio sí está versionado.
- Rama actual al diagnosticar: `feat/dockerizacion-institucional`.
- `HEAD` al diagnosticar: `7f8072f`.
- Existe al menos una etiqueta previa visible: `pre-migracion-docker-2026-02-19`.
- El árbol de trabajo no está limpio. Hay cambios locales en archivos funcionales y pruebas.
- Conclusión práctica:
  - para clon paralelo exacto del estado actual conviene primero fijar commit/tag o usar copia hermana
  - `git worktree` es recomendable solo cuando el árbol esté limpio o cuando el punto base ya quedó congelado

## 4. Compatibilidad histórica que debe respetarse

- La app visible es `tramites`.
- La compatibilidad histórica se conserva mediante `app_label`/`label` igual a `licencias`.
- Las migraciones siguen ancladas al label histórico `licencias`.
- Los permisos críticos siguen usando nombres como:
  - `licencias.view_casointerno`
  - `licencias.add_casointerno`
  - `licencias.change_casointerno`
  - `licencias.delete_casointerno`

## 5. Módulos y focos funcionales detectados

Foco principal actual confirmado:

- `/tramites/`
- `/herramientas/analizador/`

También existen y deben inventariarse, sin asumir que deban cambiarse en esta tarea:

- bandeja / cola operativa
- reportes
- licencias
- plantillas de secundarias
- gobierno de datos
- endpoints API de catálogos

## 6. Modelos clave confirmados

Confirmados en [`tramites/models.py`](/Users/admin/Documents/project_secu_juridi/tramites/models.py):

- `CCTSecundaria`
- `TipoProceso`
- `AreaProceso`
- `EstatusCaso`
- `PrefijoOficio`
- `CasoInterno`
- `HistorialEstatusCaso`

Además, se confirmó manejo real de adjuntos/minutas mediante `FileField` en modelos del dominio de casos y trámites.

## 7. Scripts existentes relevantes

Se detectaron scripts previos:

- [`scripts/backup.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backup.sh)
- [`scripts/backup_data.sh`](/Users/admin/Documents/project_secu_juridi/scripts/backup_data.sh)
- [`scripts/restore.sh`](/Users/admin/Documents/project_secu_juridi/scripts/restore.sh)
- [`scripts/validate_restore.sh`](/Users/admin/Documents/project_secu_juridi/scripts/validate_restore.sh)

Limitaciones detectadas:

- no están agrupados bajo una convención única de blindaje
- no cubren de forma homogénea Docker raíz, compose legado y `pg_dump` directo
- no dejan una carpeta por corrida claramente organizada por fecha/hora
- no separan claramente respaldo de BD, media, código, verificación y clon paralelo

## 8. Decisión de implementación para esta fase

Se implementará una capa nueva y conservadora en:

- `scripts/backups/`
- `docs/`

Objetivo de la capa nueva:

- preservar lo existente
- no romper scripts heredados
- unificar respaldo, restauración, verificación y clon paralelo
- soportar Docker y PostgreSQL directo según entorno real

## 9. Riesgos actuales detectados

- Diferencia entre `media/` del host y `/app/media` del contenedor activo.
- La ruta local `127.0.0.1:5532` no responde hoy, por lo que el flujo directo sin Docker no puede asumirse como operativo en este entorno.
- El árbol Git tiene cambios locales; un clon paralelo por `worktree` sin congelar primero puede omitir parte del estado actual.
- `backups/` ya contiene respaldos históricos, pero hoy no está preparado para versionar `backups/.gitkeep` porque la carpeta completa está ignorada en `.gitignore`.

## 10. Criterio de blindaje para los siguientes cambios

Los siguientes cambios deben:

- no tocar modelos ni migraciones históricas
- no tocar `app_label`/`label = "licencias"`
- no modificar rutas ni permisos funcionales
- dejar respaldos ejecutables y verificables
- dejar restauración documentada en español
- dejar un flujo simple para separar “original estable” y “copia de evolución”
