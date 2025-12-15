# Prompt para otra IA: eliminar rastros del módulo "Licencias" y renombrar a "Trámites"

## Objetivo
El proyecto inició como “Licencias” y migró a un dominio general de trámites. Aún hay nombres, permisos, rutas y textos visibles con “licencias”. Esta guía indica qué inspeccionar y cómo renombrar de forma consistente a “Trámites”.

## Alcance y contexto
- Framework: Django + DRF + HTMX/JS.
- App principal: `tramites`.
- Hay referencias históricas a “licencias” (app_label y textos). Mantener compatibilidad de datos/migraciones si se conserva el app_label, pero documentar plan de migración si se cambia.

## Lineamientos generales
1) Sustituir nombres, textos y permisos que refieran al módulo “Licencias” para que hablen de “Trámites”.
2) Alinear permisos, etiquetas de app (`app_label`) y nombres de BD a la nueva terminología; si cambiar `app_label` rompe migraciones, documentar y proponer el plan para migrar sin perder datos.
3) Mantener coherencia backend (permisos, modelos, settings), frontend (plantillas, JS) y documentación (README, guías, prompts).
4) Verificar que URLs/configuración Docker/PostgreSQL/plantillas no dejen “licencias” como nombre de módulo.
5) Conservar el término “licencias” solo cuando describe un tipo de trámite (ej. “licencias médicas” en el analizador).

## Puntos de inspección clave
- Configuración y base de datos:
  - `docker/docker-compose.yml`: `POSTGRES_DB=cejei_licencias`.
  - `asesores_especializados/settings.py`: BD `cejei_licencias` y SECRET_KEY con sufijo `licencias`.
  - `tramites/apps.py`: `label = "licencias"` (histórico).
- Plantillas y permisos:
  - `tramites/templates/tramites/base.html` y vistas en `tramites/templates/tramites/tramites/` usan `perms.licencias.*`.
  - `tramites/templates/tramites/herramientas/analizador_tramite.html` contiene encabezados de “Licencias médicas”.
- JavaScript:
  - `tramites/static/js/analizador-tramites.js` usa nombres `licencias`, `renderLicencias`, etc. (mantener solo como concepto de trámite médico).
- Documentación y prompts:
  - `README.md`, `LEVANTAR_PROYECTO.md`, `VERIFICACION_CAMBIOS.md`, `PROMPT_MAESTRO.md`, `DEBUG_PROMPT_PREFIJOS_CRUD.md` y otros contienen “licencias”.
  - `backup_cejei_licencias_20251212.dump`: dump histórico (referencia a BD).

## Tareas sugeridas
1) Renombrar configuración:
   - Actualizar nombres de BD y variables de entorno a “tramites”.
   - Evaluar impacto de cambiar `app_label` en `tramites/apps.py`; si se mantiene, documentar plan de migración para renombrar tablas/permisos.
2) Actualizar permisos y scope:
   - Cambiar `perms.licencias.*` a `perms.tramites.*` (o al app_label definitivo) en vistas, plantillas, validaciones.
   - Revisar permisos hardcodeados en `tramites/views.py`.
3) Revisar migraciones y fixtures:
   - Ajustar referencias en `tramites/migrations` y `tramites/fixtures/catalogos_iniciales.json` si se redefine `app_label`; documentar cómo regenerar/renombrar tablas.
4) Refrescar textos y UX:
   - Cambiar textos de sistema “Licencias” → “Trámites”; conservar “licencias médicas” como concepto de trámite.
   - Revisar encabezados en `tramites/templates/tramites/herramientas/analizador_tramite.html` y strings en JS.
5) Actualizar documentación y prompts:
   - README y guías (`LEVANTAR_PROYECTO.md`, `VERIFICACION_CAMBIOS.md`, `PROMPT_MAESTRO.md`, prompts de debug) deben reflejar el nuevo nombre.
   - Alinear ejemplos Docker/psql a la nueva BD.
6) Pruebas:
   - Ejecutar checklist de `VERIFICACION_CAMBIOS.md` después del renombrado.
   - Validar que los nuevos permisos siguen habilitando CRUDs y el analizador funciona (sin errores de imports o nombres).

## Entregable esperado
- PR que reemplace referencias a “Licencias” como módulo/sistema por “Trámites” o el `app_label` definido.
- Funcionalidad intacta del analizador y CRUDs.
- Instrucciones claras si se debe migrar `app_label` y pasos para hacerlo sin perder datos.
