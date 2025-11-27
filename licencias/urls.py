from __future__ import annotations

from django.urls import path

from licencias import views

app_name = "licencias"

urlpatterns = [
    path("", views.TramiteListView.as_view(), name="tramite-list"),
    path("tramites/nuevo/", views.TramiteCreateView.as_view(), name="tramite-create"),
    path("tramites/<int:pk>/", views.TramiteDetailView.as_view(), name="tramite-detail"),
    path(
        "tramites/<int:pk>/editar/",
        views.TramiteUpdateView.as_view(),
        name="tramite-update",
    ),
    path(
        "tramites/<int:pk>/eliminar/",
        views.TramiteDeleteView.as_view(),
        name="tramite-delete",
    ),
    path(
        "tramites/<int:pk>/etapa/",
        views.MovimientoCreateView.as_view(),
        name="tramite-cambiar-etapa",
    ),
    path("importar/", views.ImportCSVView.as_view(), name="importar-csv"),
    path("kpis/", views.KPIView.as_view(), name="kpis"),
    path("herramientas/", views.ToolIndexView.as_view(), name="herramientas-index"),
    path("herramientas/analizador/", views.TramiteEligibilityToolView.as_view(), name="analizador-tramite"),
    # Protocolos
    path("protocolos/", views.RelacionProtocoloListView.as_view(), name="protocolo-list"),
    path("protocolos/nuevo/", views.RelacionProtocoloCreateView.as_view(), name="protocolo-create"),
    path("protocolos/<int:pk>/", views.RelacionProtocoloDetailView.as_view(), name="protocolo-detail"),
    path("protocolos/<int:pk>/editar/", views.RelacionProtocoloUpdateView.as_view(), name="protocolo-update"),
    path("protocolos/<int:pk>/eliminar/", views.RelacionProtocoloDeleteView.as_view(), name="protocolo-delete"),
    # Casos internos
    path("casos-internos/", views.CasoInternoListView.as_view(), name="casointerno-list"),
    path("casos-internos/nuevo/", views.CasoInternoCreateView.as_view(), name="casointerno-create"),
    path("casos-internos/<int:pk>/", views.CasoInternoDetailView.as_view(), name="casointerno-detail"),
    path("casos-internos/<int:pk>/editar/", views.CasoInternoUpdateView.as_view(), name="casointerno-update"),
    path("casos-internos/<int:pk>/eliminar/", views.CasoInternoDeleteView.as_view(), name="casointerno-delete"),
    path(
        "casos-internos/<int:caso_id>/procesos/nuevo/",
        views.ProcesoInternoCreateView.as_view(),
        name="procesointerno-create",
    ),
    path("procesos-internos/<int:pk>/", views.ProcesoInternoDetailView.as_view(), name="procesointerno-detail"),
    path("procesos-internos/<int:pk>/editar/", views.ProcesoInternoUpdateView.as_view(), name="procesointerno-update"),
    path(
        "procesos-internos/<int:pk>/eliminar/",
        views.ProcesoInternoDeleteView.as_view(),
        name="procesointerno-delete",
    ),
    # Control de internos
    path("control-internos/", views.ControlInternoListView.as_view(), name="controlinterno-list"),
    path("control-internos/nuevo/", views.ControlInternoCreateView.as_view(), name="controlinterno-create"),
    path("control-internos/<int:pk>/", views.ControlInternoDetailView.as_view(), name="controlinterno-detail"),
    path("control-internos/<int:pk>/editar/", views.ControlInternoUpdateView.as_view(), name="controlinterno-update"),
    path("control-internos/<int:pk>/eliminar/", views.ControlInternoDeleteView.as_view(), name="controlinterno-delete"),
    path("control-internos/cct/", views.ControlInternoCCTLookupView.as_view(), name="controlinterno-cct-lookup"),
]
