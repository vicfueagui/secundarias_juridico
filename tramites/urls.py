from __future__ import annotations

from django.urls import path
from django.views.generic import RedirectView

from tramites import views

app_name = "tramites"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("operacion/cola/", views.MiColaTrabajoView.as_view(), name="mi-cola"),
    path(
        "operacion/accion-rapida/",
        views.OperacionAccionRapidaView.as_view(),
        name="operacion-accion-rapida",
    ),
    path(
        "tramites/filtros-guardados/",
        views.FiltroGuardadoUsuarioView.as_view(),
        name="filtro-guardado",
    ),
    path("bandeja/", views.BandejaEntradaListView.as_view(), name="bandeja"),
    path("bandeja/marcar-todo/", views.BandejaEntradaMarcarTodoView.as_view(), name="bandeja-marcar-todo"),
    path("bandeja/marcar/<int:pk>/", views.BandejaEntradaMarcarView.as_view(), name="bandeja-marcar"),
    # Compatibilidad con rutas antiguas (antes se llamaban "control internos")
    path(
        "control-internos/",
        RedirectView.as_view(pattern_name="tramites:casointerno-list", permanent=True),
    ),
    # Trámites
    path("tramites/", views.CasoInternoListView.as_view(), name="casointerno-list"),
    path("tramites/acciones-masivas/", views.CasoInternoBulkActionView.as_view(), name="casointerno-bulk"),
    # Licencias
    path("licencias/", views.LicenciaRegistroListView.as_view(), name="licencia-list"),
    path("licencias/nuevo/", views.LicenciaRegistroCreateView.as_view(), name="licencia-create"),
    path("licencias/<int:pk>/", views.LicenciaRegistroDetailView.as_view(), name="licencia-detail"),
    path("licencias/<int:pk>/editar/", views.LicenciaRegistroUpdateView.as_view(), name="licencia-update"),
    path("licencias/<int:pk>/eliminar/", views.LicenciaRegistroDeleteView.as_view(), name="licencia-delete"),
    path(
        "licencias/<int:pk>/estatus/agregar/",
        views.LicenciaEstatusCreateView.as_view(),
        name="licencia-estatus-create",
    ),
    path(
        "licencias/empleados/",
        views.PlantillaEmpleadoListView.as_view(),
        name="empleado-list",
    ),
    path(
        "licencias/empleados/nuevo/",
        views.PlantillaEmpleadoCreateView.as_view(),
        name="empleado-create",
    ),
    path(
        "licencias/empleados/<int:pk>/editar/",
        views.PlantillaEmpleadoUpdateView.as_view(),
        name="empleado-update",
    ),
    path(
        "licencias/empleados/<int:pk>/eliminar/",
        views.PlantillaEmpleadoDeleteView.as_view(),
        name="empleado-delete",
    ),
    path(
        "licencias/empleados/lookup/",
        views.TrabajadorLookupView.as_view(),
        name="empleado-lookup",
    ),
    path(
        "licencias/empleados/centros/agregar/",
        views.TrabajadorCentroAddView.as_view(),
        name="empleado-centro-add",
    ),
    path(
        "licencias/empleados/centros/eliminar/",
        views.TrabajadorCentroDeleteView.as_view(),
        name="empleado-centro-delete",
    ),
    path(
        "licencias/empleados/picker/",
        views.PlantillaEmpleadoPickerView.as_view(),
        name="empleado-picker",
    ),
    path(
        "licencias/empleados/picker/<int:pk>/editar/",
        views.PlantillaEmpleadoPickerEditView.as_view(),
        name="empleado-picker-edit",
    ),
    path(
        "licencias/empleados/picker/<int:pk>/eliminar/",
        views.PlantillaEmpleadoPickerDeleteView.as_view(),
        name="empleado-picker-delete",
    ),
    path("reportes/", views.ReporteCasosListView.as_view(), name="reportes-list"),
    path("reportes/print/", views.ReporteCasosPrintView.as_view(), name="reportes-print"),
    path("reportes/csv/", views.ReporteCasosCsvView.as_view(), name="reportes-csv"),
    path("tramites/nuevo/", views.CasoInternoCreateView.as_view(), name="casointerno-create"),
    path("tramites/<int:pk>/", views.CasoInternoDetailView.as_view(), name="casointerno-detail"),
    path(
        "tramites/<int:pk>/comentarios/agregar/",
        views.CasoInternoComentarioCreateView.as_view(),
        name="casointerno-comentario-create",
    ),
    path(
        "tramites/<int:pk>/tareas/agregar/",
        views.CasoInternoTareaCreateView.as_view(),
        name="casointerno-tarea-create",
    ),
    path(
        "tramites/<int:pk>/tareas/<int:tarea_pk>/completar/",
        views.CasoInternoTareaCompletarView.as_view(),
        name="casointerno-tarea-completar",
    ),
    path(
        "tramites/<int:pk>/reporte-ejecutivo/",
        views.CasoInternoReporteEjecutivoPrintView.as_view(),
        name="casointerno-reporte-ejecutivo",
    ),
    path("tramites/<int:pk>/editar/", views.CasoInternoUpdateView.as_view(), name="casointerno-update"),
    path(
        "tramites/<int:pk>/trabajadores/sincronizar/",
        views.CasoTrabajadorSyncView.as_view(),
        name="caso-trabajadores-sync",
    ),
    path("tramites/<int:pk>/eliminar/", views.CasoInternoDeleteView.as_view(), name="casointerno-delete"),
    path(
        "tramites/<int:pk>/convertir-anexo/",
        views.CasoInternoConvertirAAnexoView.as_view(),
        name="casointerno-convertir-anexo",
    ),
    path(
        "tramites/<int:pk>/minutas/<int:minuta_pk>/eliminar/",
        views.MinutaCasoDeleteView.as_view(),
        name="casointerno-minuta-delete",
    ),
    path(
        "tramites/<int:pk>/minuta/eliminar/",
        views.CasoInternoMinutaClearView.as_view(),
        name="casointerno-minuta-clear",
    ),
    path(
        "tramites/<int:pk>/estatus/agregar/",
        views.CasoInternoEstatusCreateView.as_view(),
        name="casointerno-estatus-create",
    ),
    path(
        "tramites/<int:pk>/estatus/<int:estatus_pk>/editar/",
        views.CasoInternoEstatusUpdateView.as_view(),
        name="casointerno-estatus-update",
    ),
    path(
        "tramites/<int:pk>/estatus/<int:estatus_pk>/eliminar/",
        views.CasoInternoEstatusDeleteView.as_view(),
        name="casointerno-estatus-delete",
    ),
    path(
        "tramites/<int:caso_pk>/agregar-tramite/",
        views.TramiteCasoCreateView.as_view(),
        name="tramite-caso-create",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:pk>/",
        views.TramiteCasoDetailView.as_view(),
        name="tramite-caso-detail",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:pk>/reporte-ejecutivo/",
        views.TramiteCasoReporteEjecutivoPrintView.as_view(),
        name="tramite-caso-reporte-ejecutivo",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:pk>/editar/",
        views.TramiteCasoUpdateView.as_view(),
        name="tramite-caso-update",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:pk>/eliminar/",
        views.TramiteCasoDeleteView.as_view(),
        name="tramite-caso-delete",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:tramite_pk>/minutas/<int:minuta_pk>/eliminar/",
        views.MinutaTramiteDeleteView.as_view(),
        name="tramite-caso-minuta-delete",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:tramite_pk>/minuta/eliminar/",
        views.TramiteMinutaClearView.as_view(),
        name="tramite-caso-minuta-clear",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:tramite_pk>/estatus/agregar/",
        views.TramiteCasoEstatusCreateView.as_view(),
        name="tramite-caso-estatus-create",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:tramite_pk>/definir-iniciador/",
        views.TramiteCasoDefinirIniciadorView.as_view(),
        name="tramite-caso-definir-iniciador",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:tramite_pk>/quitar-iniciador/",
        views.TramiteCasoQuitarIniciadorView.as_view(),
        name="tramite-caso-quitar-iniciador",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:pk>/promover-caso/",
        views.TramiteCasoPromoverACasoView.as_view(),
        name="tramite-caso-promover",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:tramite_pk>/estatus/<int:pk>/editar/",
        views.TramiteCasoEstatusUpdateView.as_view(),
        name="tramite-caso-estatus-update",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:tramite_pk>/estatus/<int:pk>/eliminar/",
        views.TramiteCasoEstatusDeleteView.as_view(),
        name="tramite-caso-estatus-delete",
    ),
    path("tramites/catalogos/cct/", views.CCTLookupView.as_view(), name="cct-lookup"),
    path("folios/", views.FolioRegistroListView.as_view(), name="folio-list"),
    path("folios/<int:pk>/", views.FolioRegistroDetailView.as_view(), name="folio-detail"),
    path("folios/nuevo/", views.FolioRegistroCreateView.as_view(), name="folio-create"),
    path("folios/<int:pk>/editar/", views.FolioRegistroUpdateView.as_view(), name="folio-update"),
    path("folios/<int:pk>/eliminar/", views.FolioRegistroDeleteView.as_view(), name="folio-delete"),
    path("folios/<int:pk>/reactivar/", views.FolioRegistroReactivarView.as_view(), name="folio-reactivar"),
    path("folios/generar/", views.FolioGenerarView.as_view(), name="folio-generar"),
    path("folios/generar/preview/", views.FolioGenerarPreviewView.as_view(), name="folio-generar-preview"),
    path("folios/generar/cancelar/", views.FolioGenerarCancelarView.as_view(), name="folio-generar-cancelar"),
    path("folios/buscar/", views.FolioBuscarView.as_view(), name="folio-buscar"),
    path(
        "tramites/<int:pk>/folio/generar/",
        views.CasoInternoGenerarFolioView.as_view(),
        name="casointerno-folio-generar",
    ),
    path(
        "tramites/<int:caso_pk>/tramites-caso/<int:pk>/folio/generar/",
        views.TramiteCasoGenerarFolioView.as_view(),
        name="tramite-caso-folio-generar",
    ),
    path(
        "tramites/duplicados/preview/",
        views.DuplicadosPreviewView.as_view(),
        name="duplicados-preview",
    ),
    path(
        "tramites/documentos/preview-data/",
        views.DocumentoPreviewDataView.as_view(),
        name="documento-preview-data",
    ),
    # Herramientas
    path("herramientas/", views.ToolIndexView.as_view(), name="herramientas-index"),
    path(
        "herramientas/gobierno-datos/",
        views.DataGovernanceView.as_view(),
        name="gobierno-datos",
    ),
    path("herramientas/analizador/", views.TramiteEligibilityToolView.as_view(), name="analizador-tramite"),
    path(
        "herramientas/plantillas-secundarias/",
        views.PlantillaSecundariasToolView.as_view(),
        name="plantillas-secundarias",
    ),
]
