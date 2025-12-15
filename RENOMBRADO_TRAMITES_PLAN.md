# Plan seguro para eliminar referencias a “Licencias” y usar “Trámites” sin perder datos

## Contexto actual
- La app principal es `tramites` pero mantiene `app_label = "licencias"` para conservar tablas y permisos existentes.
- La base de datos y variables de entorno usan el prefijo `cejei_licencias`.
- Plantillas usan `perms.licencias.*` porque el app_label histórico define los codenames.

## Decisión de compatibilidad
- **No se cambia el `app_label` en caliente**: hacerlo renombraría tablas y contenttypes, con alto riesgo de pérdida de datos. En su lugar, se limpian textos visibles y se documenta el plan de migración.
- El término “licencias” solo se conserva como concepto de dominio (ej. licencias médicas en el analizador).

## Plan de migración (si se desea renombrar definitivamente)
1) **Respaldo**: `pg_dump` de la BD actual y exportación de permisos (contenttypes/permissions y auth tables).
2) **Preparar nuevo app_label**:
   - Cambiar `tramites/apps.py` a `label = "tramites"`.
   - Ajustar fixtures, migraciones y permisos a `tramites.*`.
   - Generar migraciones de renombrado de tablas (`AlterModelTable`) o aplicar `RunSQL` con `ALTER TABLE licencias_* RENAME TO tramites_*`.
   - Migrar contenttypes/permissions: actualizar `django_content_type` y `auth_permission` (`app_label` → `tramites`) en una data migration.
3) **Variables de entorno/infra**:
   - Renombrar BD a `cejei_tramites` o apuntar a una nueva BD y restaurar dump.
   - Actualizar Docker compose, settings y secrets.
4) **Despliegue**:
   - Aplicar migraciones en ambiente de staging con datos reales.
   - Ejecutar suite de pruebas y checklist de `VERIFICACION_CAMBIOS.md`.
5) **Corte a producción**:
   - Ventana de mantenimiento breve.
   - Backup inmediato + migraciones + validación funcional.

## Acciones ya aplicadas
- Se mantiene compatibilidad de datos: no se toca `app_label` ni nombres de tablas.
- Prompt de trabajo para IA (`PROMPT_RENOMBRAR_TRAMITES.md`) con las rutas críticas a revisar y lineamientos de reemplazo de textos/permisos/documentación.

## Pendientes recomendados (sin afectar datos)
- Actualizar documentación y textos visibles a “Trámites”.
- Mantener `perms.licencias.*` en código hasta ejecutar el plan de migración para evitar romper accesos.
- Validar periódicamente que los textos de UI no usen “Licencias” salvo concepto de trámite médico.
