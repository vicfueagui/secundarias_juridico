from __future__ import annotations

from rest_framework.routers import DefaultRouter

from tramites import views

app_name = "tramites_api"

router = DefaultRouter()
router.register("ccts", views.CCTSecundariaViewSet, basename="cct")
router.register("tipos-proceso", views.TipoProcesoViewSet, basename="tipo-proceso")
router.register("estatus-caso", views.EstatusCasoViewSet, basename="estatus-caso")
router.register("prefijos-oficio", views.PrefijoOficioViewSet, basename="prefijo-oficio")
router.register("tipos-violencia", views.TipoViolenciaViewSet, basename="tipo-violencia")
router.register("solicitantes", views.SolicitanteViewSet, basename="solicitante")
router.register("destinatarios", views.DestinatarioViewSet, basename="destinatario")
router.register("tramites-caso", views.TramiteCasoViewSet, basename="tramite-caso")
router.register("estatus-tramite", views.EstatusTramiteViewSet, basename="estatus-tramite")

urlpatterns = router.urls
