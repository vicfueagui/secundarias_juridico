# Paso 5 - Estrategia de Datos (Obligatoria)

Fecha de ejecución: 2026-02-20
Rama: chore/prep-migracion-docker

## Regla de validez

Un backup **no se considera válido** si no pasa una prueba de restore en entorno aparte.

## Estrategia definida

1. Generar backup de base de datos PostgreSQL.
2. Generar backup de archivos `media/`.
3. Crear manifest con hashes y conteo de archivos.
4. Restaurar DB en una base temporal aislada (`restore_test_*`).
5. Restaurar `media` en carpeta temporal de validación.
6. Comparar métricas origen vs restaurado.
7. Emitir veredicto de validez.

## Scripts implementados

- `scripts/backup_data.sh`
  - Genera:
    - `backups/db_<timestamp>.dump`
    - `backups/media_<timestamp>.tar.gz`
    - `backups/backup_<timestamp>.manifest`
- `scripts/validate_restore.sh`
  - Restaura dump en DB temporal.
  - Extrae media en ruta temporal.
  - Compara tablas/migraciones/conteo de archivos.
  - Produce `backups/restore_validation_<timestamp>.md`.

## Evidencia de ejecución real

### Backup generado

- `backups/db_20260220_102204.dump`
- `backups/media_20260220_102204.tar.gz`
- `backups/backup_20260220_102204.manifest`

Valores del manifest:

- `db_sha256=27f8c5d2873726f76d5f0b2949cbd2c3771ee648bd0d3f65dae60a2aea69233e`
- `media_sha256=7e9a6c675b9bf1053d9529ad5008f591ca6358bc52c5c000878d2d3ccd942a6f`
- `media_file_count=359`

### Restore probado en entorno aparte

Reporte:

- `backups/restore_validation_20260220_102313.md`

Resultados:

- Tablas DB origen/restaurada: `72 / 72`
- `django_migrations` origen/restaurada: `82 / 82`
- Archivos media origen/restaurados: `359 / 359`
- Veredicto: `VALIDADO`

## Conclusión Paso 5

- Backup de BD + media: **completado**.
- Restore en entorno aparte: **completado y validado**.
- Criterio obligatorio: **cumplido**.
