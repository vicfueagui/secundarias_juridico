"""Vistas HTML y API para el módulo de licencias."""
from __future__ import annotations

import logging
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, FormView, TemplateView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django_filters.views import FilterView
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from licencias import filters, forms, models, serializers
from licencias.utils import normalise_sistema
from licencias.services import import_csv, kpi_queries, validators

logger = logging.getLogger(__name__)


_CCT_CATALOG_LOADED = False


def ensure_cct_catalog_loaded() -> None:
    """Verifica una sola vez si existen CCT cargados."""
    global _CCT_CATALOG_LOADED
    if _CCT_CATALOG_LOADED:
        return
    try:
        if models.CCTSecundaria.objects.exists():
            _CCT_CATALOG_LOADED = True
        else:
            logger.warning(
                "Catálogo de CCT vacío. Ejecuta `python manage.py import_ccts --path cct_secundarias.csv`."
            )
            _CCT_CATALOG_LOADED = True
    except DatabaseError:
        logger.warning("No se pudo verificar el catálogo de CCT (base de datos no disponible).")


# --------------------------------------------------------------------------- #
# Vistas HTML (Django templates + HTMX)
# --------------------------------------------------------------------------- #


def registrar_cambio_estatus(
    control: models.ControlInterno,
    usuario,
    estatus_anterior: str | None,
    estatus_nuevo: str | None,
) -> None:
    """Genera un registro en el historial de estatus cuando hay cambios."""
    anterior = (estatus_anterior or "").strip()
    nuevo = (estatus_nuevo or "").strip()
    if anterior == nuevo:
        return
    actor = usuario if getattr(usuario, "is_authenticated", False) else None
    models.ControlInternoStatusHistory.objects.create(
        control=control,
        estatus_anterior=anterior,
        estatus_nuevo=nuevo,
        cambiado_por=actor,
    )


class TramiteListView(LoginRequiredMixin, FilterView):
    """Lista y filtros de trámites."""

    model = models.Tramite
    paginate_by = 25
    filterset_class = filters.TramiteFilter
    template_name = "licencias/tramite_list.html"
    context_object_name = "tramites"
    ordering = "-updated_at"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "tipo_tramite",
                "subsistema",
                "sindicato",
                "estado_actual",
                "resultado_resolucion",
                "user_responsable",
            )
        )


class RelacionProtocoloListView(
    LoginRequiredMixin, PermissionRequiredMixin, FilterView
):
    """Listado de la relación de protocolos."""

    permission_required = "licencias.view_relacionprotocolo"
    model = models.RelacionProtocolo
    paginate_by = 25
    filterset_class = filters.RelacionProtocoloFilter
    template_name = "licencias/protocolos/protocolo_list.html"
    context_object_name = "protocolos"
    ordering = "-fecha_inicio"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("cct")
        )


class TramiteDetailView(LoginRequiredMixin, DetailView):
    model = models.Tramite
    template_name = "licencias/tramite_detail.html"
    context_object_name = "tramite"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["movimiento_form"] = forms.MovimientoForm()
        return ctx


class TramiteCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "licencias.add_tramite"
    model = models.Tramite
    template_name = "licencias/tramite_form.html"
    form_class = forms.TramiteForm
    success_url = reverse_lazy("licencias:tramite-list")

    def form_valid(self, form: forms.TramiteForm) -> HttpResponse:
        form.instance.user_responsable = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, _("Trámite creado correctamente."))
        return response


class TramiteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "licencias.change_tramite"
    model = models.Tramite
    template_name = "licencias/tramite_form.html"
    form_class = forms.TramiteForm
    success_url = reverse_lazy("licencias:tramite-list")

    def form_valid(self, form: forms.TramiteForm) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, _("Trámite actualizado."))
        return response


class TramiteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "licencias.delete_tramite"
    model = models.Tramite
    template_name = "licencias/tramite_confirm_delete.html"
    success_url = reverse_lazy("licencias:tramite-list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        messages.success(request, _("Trámite eliminado."))
        return super().delete(request, *args, **kwargs)


class MovimientoCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "licencias.add_movimiento"
    form_class = forms.MovimientoForm
    template_name = "licencias/partials/movimiento_form.html"

    def form_valid(self, form: forms.MovimientoForm) -> HttpResponse:
        tramite = get_object_or_404(models.Tramite, pk=self.kwargs["pk"])
        movimiento = form.save(commit=False)
        movimiento.tramite = tramite
        movimiento.etapa_anterior = tramite.estado_actual
        movimiento.usuario = self.request.user
        try:
            validators.validar_transicion_etapa(
                tramite.estado_actual, movimiento.etapa_nueva
            )
        except ValidationError as exc:
            messages.error(self.request, exc)
            if self.request.headers.get("HX-Request") == "true":
                return JsonResponse({"success": False, "error": str(exc)}, status=400)
            return redirect("licencias:tramite-detail", pk=tramite.pk)
        tramite.estado_actual = movimiento.etapa_nueva
        tramite.save()
        movimiento.save()
        messages.success(self.request, _("Etapa actualizada correctamente."))
        if self.request.headers.get("HX-Request") == "true":
            return JsonResponse({"success": True})
        return redirect("licencias:tramite-detail", pk=tramite.pk)


class ImportCSVView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "licencias.add_tramite"
    template_name = "licencias/import_preview.html"
    form_class = forms.ImportCSVForm
    success_url = reverse_lazy("licencias:importar-csv")

    def form_valid(self, form: forms.ImportCSVForm) -> HttpResponse:
        archivo = form.cleaned_data["archivo"]
        crear = form.cleaned_data["crear_catalogos"]
        resultado = import_csv.procesar_archivo(
            archivo=archivo, crear_catalogos=crear, usuario=self.request.user
        )
        context = self.get_context_data(form=form, resultado=resultado)
        return self.render_to_response(context)


class KPIView(LoginRequiredMixin, TemplateView):
    template_name = "licencias/kpis.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.update(kpi_queries.obtener_kpis_resumen())
        return ctx


class CCTCatalogContextMixin:
    """Proporciona en el contexto el catálogo y endpoints relacionados con CCT."""

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ensure_cct_catalog_loaded()
        catalogo = list(
            models.CCTSecundaria.objects.order_by("cct").values(
                "cct", "nombre", "servicio", "asesor", "sostenimiento"
            )
        )
        for item in catalogo:
            item["sostenimiento"] = normalise_sistema(item.get("sostenimiento"))
        ctx["cct_catalogo"] = catalogo
        ctx["cct_lookup_url"] = reverse_lazy("licencias:controlinterno-cct-lookup")
        ctx["cct_api_url"] = reverse_lazy("licencias_api:cct-list")
        return ctx


class RelacionProtocoloCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, CCTCatalogContextMixin, CreateView
):
    permission_required = "licencias.add_relacionprotocolo"
    model = models.RelacionProtocolo
    form_class = forms.RelacionProtocoloForm
    template_name = "licencias/protocolos/protocolo_form.html"
    success_url = reverse_lazy("licencias:protocolo-list")

    def form_valid(self, form: forms.RelacionProtocoloForm) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, _("Protocolo registrado correctamente."))
        return response


class RelacionProtocoloUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, CCTCatalogContextMixin, UpdateView
):
    permission_required = "licencias.change_relacionprotocolo"
    model = models.RelacionProtocolo
    form_class = forms.RelacionProtocoloForm
    template_name = "licencias/protocolos/protocolo_form.html"
    success_url = reverse_lazy("licencias:protocolo-list")

    def form_valid(self, form: forms.RelacionProtocoloForm) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, _("Protocolo actualizado."))
        return response


class RelacionProtocoloDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "licencias.view_relacionprotocolo"
    model = models.RelacionProtocolo
    template_name = "licencias/protocolos/protocolo_detail.html"
    context_object_name = "protocolo"


class RelacionProtocoloDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, DeleteView
):
    permission_required = "licencias.delete_relacionprotocolo"
    model = models.RelacionProtocolo
    template_name = "licencias/protocolos/protocolo_confirm_delete.html"
    success_url = reverse_lazy("licencias:protocolo-list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        messages.success(request, _("Registro eliminado."))
        return super().delete(request, *args, **kwargs)


class ControlInternoFormMixin(CCTCatalogContextMixin):
    """Mixin para compartir contexto y configuración de formularios."""


class ControlInternoListView(
    LoginRequiredMixin, PermissionRequiredMixin, FilterView
):
    """Listado y filtros de controles internos."""

    permission_required = "licencias.view_controlinterno"
    model = models.ControlInterno
    paginate_by = 25
    filterset_class = filters.ControlInternoFilter
    template_name = "licencias/control_internos/controlinterno_list.html"
    context_object_name = "controles"
    ordering = "-fecha_memorandum"

    def get_queryset(self):
        return super().get_queryset().select_related("cct")


class ControlInternoCreateView(
    ControlInternoFormMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    """Formulario para registrar un control interno."""

    permission_required = "licencias.add_controlinterno"
    model = models.ControlInterno
    form_class = forms.ControlInternoForm
    template_name = "licencias/control_internos/controlinterno_form.html"
    success_url = reverse_lazy("licencias:controlinterno-list")

    def form_valid(self, form: forms.ControlInternoForm) -> HttpResponse:
        response = super().form_valid(form)
        registrar_cambio_estatus(
            control=self.object,
            usuario=self.request.user,
            estatus_anterior=None,
            estatus_nuevo=self.object.estatus,
        )
        messages.success(self.request, _("Control interno registrado correctamente."))
        return response


class ControlInternoDetailView(
    ControlInternoFormMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView
):
    """Detalle de un control interno y su historial de estatus."""

    permission_required = "licencias.view_controlinterno"
    model = models.ControlInterno
    template_name = "licencias/control_internos/controlinterno_detail.html"
    context_object_name = "control"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["estatus_historial"] = self.object.estatus_historial.select_related("cambiado_por")
        return ctx


class ControlInternoUpdateView(
    ControlInternoFormMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView
):
    """Formulario para actualizar un control interno."""

    permission_required = "licencias.change_controlinterno"
    model = models.ControlInterno
    form_class = forms.ControlInternoForm
    template_name = "licencias/control_internos/controlinterno_form.html"
    success_url = reverse_lazy("licencias:controlinterno-list")

    def form_valid(self, form: forms.ControlInternoForm) -> HttpResponse:
        old_status = self.object.estatus
        response = super().form_valid(form)
        registrar_cambio_estatus(
            control=self.object,
            usuario=self.request.user,
            estatus_anterior=old_status,
            estatus_nuevo=self.object.estatus,
        )
        messages.success(self.request, _("Control interno actualizado."))
        return response


class ControlInternoDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, DeleteView
):
    """Eliminar un control interno."""

    permission_required = "licencias.delete_controlinterno"
    model = models.ControlInterno
    template_name = "licencias/control_internos/controlinterno_confirm_delete.html"
    success_url = reverse_lazy("licencias:controlinterno-list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        messages.success(request, _("Control interno eliminado."))
        return super().delete(request, *args, **kwargs)


class ControlInternoCCTLookupView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Devuelve información del CCT desde el catálogo de secundarias."""

    permission_required = "licencias.add_controlinterno"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        codigo = (request.GET.get("cct") or "").strip().upper()
        if len(codigo) < 5:
            return JsonResponse({"found": False, "error": "CCT demasiado corto."}, status=200)
        ensure_cct_catalog_loaded()
        try:
            cct_obj = models.CCTSecundaria.objects.get(cct__iexact=codigo)
        except models.CCTSecundaria.DoesNotExist:
            return JsonResponse({"found": False}, status=200)
        return JsonResponse(
            {
                "found": True,
                "cct": cct_obj.cct,
                "c_nombre": cct_obj.nombre,
                "sostenimiento_c_subcontrol": normalise_sistema(cct_obj.sostenimiento),
                "tiponivelsub_c_servicion3": cct_obj.servicio or "",
                "asesor": cct_obj.asesor or "",
            }
        )


# --------------------------------------------------------------------------- #
# API REST (DRF)
# --------------------------------------------------------------------------- #


class CCTSecundariaViewSet(viewsets.ModelViewSet):
    queryset = models.CCTSecundaria.objects.all().order_by("cct")
    serializer_class = serializers.CCTSecundariaSerializer
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = "cct"
    lookup_value_regex = "[^/]+"
    search_fields = ("cct", "nombre", "asesor", "servicio", "municipio", "turno")
    ordering_fields = ("cct", "nombre", "municipio", "turno")

    def get_queryset(self):
        ensure_cct_catalog_loaded()
        return super().get_queryset()

    def get_object(self):
        lookup_value = self.kwargs.get(self.lookup_field)
        if lookup_value is None:
            return super().get_object()
        queryset = self.filter_queryset(self.get_queryset())
        try:
            return queryset.get(cct__iexact=lookup_value)
        except models.CCTSecundaria.DoesNotExist as exc:
            raise Http404 from exc

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_cctsecundaria"):
            raise permissions.PermissionDenied("No tienes permisos para crear CCT.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_cctsecundaria"):
            raise permissions.PermissionDenied("No tienes permisos para editar CCT.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_cctsecundaria"):
            raise permissions.PermissionDenied("No tienes permisos para eliminar CCT.")
        instance.delete()


class BaseCatalogoViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ["get", "post", "patch", "put", "delete"]


class TramiteViewSet(viewsets.ModelViewSet):
    queryset = models.Tramite.objects.all().select_related(
        "tipo_tramite",
        "subsistema",
        "diagnostico",
        "sindicato",
        "resultado_resolucion",
        "estado_actual",
        "user_responsable",
    )
    permission_classes = (permissions.IsAuthenticated,)
    filterset_class = filters.TramiteFilter
    search_fields = ("folio", "trabajador_nombre", "oficio_origen_num")
    ordering_fields = (
        "folio",
        "trabajador_nombre",
        "fecha_recepcion_nivel",
        "updated_at",
    )

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.TramiteListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return serializers.TramiteWriteSerializer
        return serializers.TramiteSerializer

    def perform_create(self, serializer):
        serializer.save(user_responsable=self.request.user)

    @action(detail=False, methods=["get"], pagination_class=None)
    def kpis(self, request):
        datos = kpi_queries.obtener_kpis_resumen()
        return Response(datos)


class OficioViewSet(viewsets.ModelViewSet):
    queryset = models.Oficio.objects.all().select_related("tramite", "area_emisora")
    serializer_class = serializers.OficioSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ("tipo", "tramite")


class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = models.Notificacion.objects.all().select_related("tramite")
    serializer_class = serializers.NotificacionSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ("destinatario", "tramite")


class MovimientoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = models.Movimiento.objects.all().select_related(
        "tramite", "etapa_anterior", "etapa_nueva", "usuario"
    )
    serializer_class = serializers.MovimientoSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ("tramite", "etapa_nueva")


class SubsistemaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Subsistema.objects.all()
    serializer_class = serializers.SubsistemaSerializer
    permission_classes = (permissions.IsAuthenticated,)


class TipoTramiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.TipoTramite.objects.all()
    serializer_class = serializers.TipoTramiteSerializer
    permission_classes = (permissions.IsAuthenticated,)


class EtapaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Etapa.objects.all()
    serializer_class = serializers.EtapaSerializer
    permission_classes = (permissions.IsAuthenticated,)


class ResultadoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Resultado.objects.all()
    serializer_class = serializers.ResultadoSerializer
    permission_classes = (permissions.IsAuthenticated,)


class AreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Area.objects.all()
    serializer_class = serializers.AreaSerializer
    permission_classes = (permissions.IsAuthenticated,)


class SindicatoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Sindicato.objects.all()
    serializer_class = serializers.SindicatoSerializer
    permission_classes = (permissions.IsAuthenticated,)


class DiagnosticoViewSet(BaseCatalogoViewSet):
    queryset = models.Diagnostico.objects.all()
    serializer_class = serializers.DiagnosticoSerializer
