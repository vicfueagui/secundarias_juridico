# Migración Docker - Alcance y Criterio de Éxito

Fecha: 2026-02-19
Responsable: admin
Rama: chore/prep-migracion-docker
Tag base (rollback): pre-migracion-docker-2026-02-19 (e336b8f)

## 1) Alcance (In Scope)
- Contenerizar Django con Gunicorn.
- Base de datos PostgreSQL en contenedor.
- Redis en contenedor.
- Worker de tareas de fondo (según implementación real del proyecto; comandos base: `run_async_jobs` y `schedule_async_jobs`).
- Nginx como reverse proxy.
- Persistencia con volúmenes para:
  - Base de datos (`postgres_data`)
  - Archivos media (`media_data`)
  - Archivos static (`static_data`)
- Configuración por `.env` (sin secretos hardcodeados).
- Scripts de backup y restore (DB + media).
- Documentación de despliegue, actualización y recuperación.

## 2) Fuera de alcance (Out of Scope)
- Rediseño funcional del sistema.
- Refactor mayor de lógica de negocio.
- Cambio de framework de colas (si no existe Celery/RQ, no introducirlo sin aprobación).
- Optimización avanzada de performance.
- Certificados TLS productivos (solo opcional/local institucional).

## 3) Funcionalidades críticas que deben seguir funcionando
- Login/logout.
- CRUD principal del módulo core del sistema (`tramites`).
- Subida/descarga de adjuntos (media).
- Generación de reportes PDF.
- Ejecución de jobs en background.

## 4) Definition of Done (DoD) medible
Se considera terminado solo si:
- [ ] `docker compose up -d --build` termina sin errores.
- [ ] `docker compose ps` muestra `db`, `redis`, `web`, `worker`, `nginx` arriba.
- [ ] Migraciones aplicadas sin error.
- [ ] Login funcional con usuario de prueba.
- [ ] CRUD principal completo: crear, listar, editar, eliminar.
- [ ] Adjuntos: se sube un archivo y queda accesible.
- [ ] Persistencia validada: reiniciar contenedores y el archivo sigue disponible.
- [ ] PDF se genera y descarga correctamente (archivo válido).
- [ ] Worker procesa al menos 1 job real o de prueba.
- [ ] Nginx sirve `/static/` y `/media/`.
- [ ] Backup genera dump DB + paquete media en `./backups/`.
- [ ] Restore recupera datos + media en entorno de prueba.
- [ ] Logs sin errores críticos (sin tracebacks durante smoke test).

## 5) Checklist de Smoke Tests (evidencia obligatoria)

### A. Infraestructura
- [ ] Comando: `docker compose up -d --build`
  - Esperado: build y arranque exitoso.
- [ ] Comando: `docker compose ps`
  - Esperado: servicios `Up` / `healthy` cuando aplique.

### B. Aplicación
- [ ] Abrir `/login` y autenticar usuario.
  - Esperado: acceso exitoso y redirección correcta.
- [ ] CRUD principal (1 registro de prueba).
  - Esperado: operaciones completas sin error.

### C. Media y PDF
- [ ] Subir adjunto (PDF/imagen de prueba).
  - Esperado: archivo disponible desde `/media/...`.
- [ ] Generar reporte PDF.
  - Esperado: descarga correcta y apertura del PDF.

### D. Worker/Jobs
- [ ] Encolar/ejecutar job de prueba.
  - Esperado: job en estado exitoso y sin errores en logs del worker.

### E. Persistencia
- [ ] `docker compose restart` y revalidar:
  - registro creado
  - archivo media
  - acceso normal
  - Esperado: todo persiste.

### F. Backup/Restore
- [ ] Ejecutar script de backup.
  - Esperado: archivos con timestamp en `./backups/`.
- [ ] Ejecutar restore en entorno de prueba.
  - Esperado: datos y media recuperados correctamente.

## 6) Cómo ejecutar smoke tests (semiautomático)

Script oficial de validación:

```bash
./smoke_test.sh --help
```

### 6.1 Validación rápida del estado actual (stack parcial)

Usar mientras el compose actual solo tenga `postgres` y `web`:

```bash
SMOKE_EXPECTED_SERVICES="postgres web" \
./smoke_test.sh --skip-up --skip-restart --compose-file docker/docker-compose.yml
```

### 6.2 Validación completa objetivo de migración

Usar cuando el stack final esté implementado (`db redis web worker nginx`):

```bash
SMOKE_EXPECTED_SERVICES="db redis web worker nginx" \
SMOKE_USER="<usuario_prueba>" \
SMOKE_PASSWORD="<password_prueba>" \
SMOKE_PDF_URL="/tramites/<id>/reporte-ejecutivo/" \
SMOKE_BACKUP_CMD="./scripts/backup.sh" \
SMOKE_RESTORE_CMD="./scripts/restore.sh <ruta_backup>" \
./smoke_test.sh --interactive --strict
```

### 6.3 Evidencia obligatoria a conservar

- Archivo de reporte generado por script en `./smoke_test_reports/`.
- Salida de `docker compose ps`.
- Evidencia manual de login, CRUD, adjunto y PDF (capturas o bitácora corta).

### 6.4 Criterio de interpretación

- `PASS`: criterio validado.
- `WARN`: pendiente manual o no concluyente.
- `FAIL`: incumplimiento directo del DoD.
- Exit code `0`: sin `FAIL`.
- Exit code `1`: al menos un `FAIL`.
- Exit code `2`: sin `FAIL` pero con `WARN` en modo `--strict`.

## Mini-acta de cierre del Paso 2
Alcance aprobado: No (pendiente de aprobación)
DoD aprobado: No (pendiente de aprobación)
Responsable de validación: Por definir
Fecha de aprobación: Pendiente
