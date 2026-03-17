# Inventario de Módulos Actuales

## 1. Estado del sistema

`project_secu_juridi` ya funciona como activo institucional. No debe tratarse como sandbox. La prioridad correcta es protegerlo, documentarlo y después evolucionarlo.

Compatibilidad histórica no negociable:

- la app operativa es `tramites`
- conserva `label = "licencias"` en [`tramites/apps.py`](/Users/admin/Documents/project_secu_juridi/tramites/apps.py)
- las migraciones históricas siguen ancladas al app label `licencias`
- los permisos siguen el namespace `licencias.*`

## 2. Foco funcional actual

Foco principal confirmado:

- módulo **Trámites** en `/tramites/`
- herramienta **Analizador de requisitos** en `/herramientas/analizador/`

Eso no elimina otros componentes activos del sistema. Solo marca dónde está hoy el valor operativo principal.

## 3. Rutas principales

Rutas HTML principales detectadas en [`tramites/urls.py`](/Users/admin/Documents/project_secu_juridi/tramites/urls.py):

- `/tramites/`
  - listado, alta, edición, detalle, eliminación, acciones masivas, historial y adjuntos
- `/herramientas/`
  - índice del centro de herramientas
- `/herramientas/analizador/`
  - analizador de requisitos
- `/herramientas/plantillas-secundarias/`
  - consulta de plantillas de secundarias
- `/herramientas/gobierno-datos/`
  - gobierno de datos
- `/bandeja/`
  - bandeja/notificaciones
- `/operacion/cola/`
  - cola de trabajo operativa
- `/reportes/`
  - vistas de reporte, impresión y CSV
- `/licencias/`
  - rutas heredadas/conviventes
- `/api/`
  - catálogos y recursos REST

Rutas API detectadas en [`tramites/api_urls.py`](/Users/admin/Documents/project_secu_juridi/tramites/api_urls.py):

- `/api/ccts/`
- `/api/tipos-proceso/`
- `/api/estatus-caso/`
- `/api/prefijos-oficio/`
- `/api/prefijos-folio/`
- `/api/tipos-violencia/`
- `/api/solicitantes/`
- `/api/destinatarios/`
- `/api/tramites-caso/`
- `/api/estatus-tramite/`
- `/api/sla-reglas/`

## 4. Modelos clave

Modelos confirmados en [`tramites/models.py`](/Users/admin/Documents/project_secu_juridi/tramites/models.py):

- `CCTSecundaria`
- `TipoProceso`
- `AreaProceso`
- `EstatusCaso`
- `PrefijoOficio`
- `CasoInterno`
- `HistorialEstatusCaso`

Modelos de soporte activos y relevantes:

- `TramiteCaso`
- modelos de minutas y adjuntos
- `PlantillaCentroTrabajo`
- `PlantillaEmpleado`
- `PlantillaRegistro`
- modelos de folios
- modelos de SLA, feature flags, bandeja y calidad de datos

Observación clave:

- sí existen `FileField` reales para minutas y adjuntos
- sí existe historial real de cambios de estatus

## 5. Permisos principales

Permisos núcleo sobre trámites:

- `licencias.view_casointerno`
- `licencias.add_casointerno`
- `licencias.change_casointerno`
- `licencias.delete_casointerno`

Otros permisos operativos activos detectados:

- `licencias.view_tramitecaso`
- `licencias.add_tramitecaso`
- `licencias.change_tramitecaso`
- `licencias.delete_tramitecaso`
- permisos de catálogos (`tipoproceso`, `estatuscaso`, `prefijooficio`, etc.)
- permisos de reportes, folios, feature flags, bandeja y gobierno de datos

## 6. Dependencias delicadas

- PostgreSQL como base principal
- `.env` para configuración operativa
- `docker-compose.yml` en raíz como stack activo validado hoy
- `docker/docker-compose.yml` como stack legado coexistente
- `media` con adjuntos reales
- `simple_history` para historial
- Redis/worker en el stack Docker actual
- carga inicial del catálogo CCT:
  - `python manage.py import_ccts --path "cct_secundarias.csv"`

## 7. Compatibilidad histórica

Esto debe quedar explícito para cualquier evolución futura:

- `tramites` conserva `app_label="licencias"` por compatibilidad histórica
- no se deben romper tablas ni migraciones existentes
- no se deben renombrar permisos `licencias.*`
- el sistema actual ya funciona como activo y no como experimento

## 8. Riesgos detectados hoy

- El árbol Git está sucio; `git worktree` no captura cambios locales no confirmados.
- `media/` del host no coincide con `/app/media` del contenedor activo.
- La ruta directa `127.0.0.1:5532` no respondió en esta revisión; no debe asumirse como camino principal.
- `nginx` del stack raíz aparece `unhealthy`, aunque `web`, `db`, `redis` y `worker` sí estaban operativos.
- Hay scripts heredados de backup/restore en `scripts/`, pero la operación formal ahora debe concentrarse en `scripts/backups/`.

## 9. Conclusión ejecutiva

La base funcional actual es aprovechable y valiosa. La decisión correcta en esta etapa es preservar:

- compatibilidad histórica
- respaldos verificables
- trazabilidad mínima
- separación clara entre entorno estable y copia de evolución
