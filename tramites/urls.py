from __future__ import annotations

from django.urls import path
from django.views.generic import RedirectView

from tramites import views

app_name = "tramites"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="tramites:casointerno-list", permanent=False)),
    # Compatibilidad con rutas antiguas (antes se llamaban "control internos")
    path(
        "control-internos/",
        RedirectView.as_view(pattern_name="tramites:casointerno-list", permanent=True),
    ),
    # Trámites
    path("tramites/", views.CasoInternoListView.as_view(), name="casointerno-list"),
    path("tramites/nuevo/", views.CasoInternoCreateView.as_view(), name="casointerno-create"),
    path("tramites/<int:pk>/", views.CasoInternoDetailView.as_view(), name="casointerno-detail"),
    path("tramites/<int:pk>/editar/", views.CasoInternoUpdateView.as_view(), name="casointerno-update"),
    path("tramites/<int:pk>/eliminar/", views.CasoInternoDeleteView.as_view(), name="casointerno-delete"),
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
        "tramites/<int:caso_pk>/tramites-caso/<int:tramite_pk>/estatus/agregar/",
        views.TramiteCasoEstatusCreateView.as_view(),
        name="tramite-caso-estatus-create",
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
    # Herramientas
    path("herramientas/", views.ToolIndexView.as_view(), name="herramientas-index"),
    path("herramientas/analizador/", views.TramiteEligibilityToolView.as_view(), name="analizador-tramite"),
]
