from __future__ import annotations

from rest_framework.routers import DefaultRouter

from licencias import views

app_name = "licencias_api"

router = DefaultRouter()
router.register("tramites", views.TramiteViewSet, basename="tramite")
router.register("oficios", views.OficioViewSet, basename="oficio")
router.register("notificaciones", views.NotificacionViewSet, basename="notificacion")
router.register("movimientos", views.MovimientoViewSet, basename="movimiento")
router.register("subsistemas", views.SubsistemaViewSet, basename="subsistema")
router.register("tipos-tramite", views.TipoTramiteViewSet, basename="tipo-tramite")
router.register("etapas", views.EtapaViewSet, basename="etapa")
router.register("resultados", views.ResultadoViewSet, basename="resultado")
router.register("areas", views.AreaViewSet, basename="area")
router.register("sindicatos", views.SindicatoViewSet, basename="sindicato")
router.register("diagnosticos", views.DiagnosticoViewSet, basename="diagnostico")
router.register("ccts", views.CCTSecundariaViewSet, basename="cct")

urlpatterns = router.urls
