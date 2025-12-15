"""Vistas HTML y API para el módulo de trámites jurídicos."""
from __future__ import annotations

import logging
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import DatabaseError, models as dj_models
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, TemplateView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.edit import FormView
from django_filters.views import FilterView
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from tramites import filters, forms, models, serializers
from tramites.utils import normalise_sistema

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


def registrar_cambio_estatus_caso(
    caso: models.CasoInterno,
    usuario,
    estatus_anterior: models.EstatusCaso | None,
    estatus_nuevo: models.EstatusCaso | None,
    comentario: str = "",
) -> None:
    """Registra en la bitácora cuando el estatus del trámite cambia."""
    actor = usuario if getattr(usuario, "is_authenticated", False) else None
    models.HistorialEstatusCaso.objects.create(
        caso=caso,
        estatus_anterior=estatus_anterior,
        estatus_nuevo=estatus_nuevo,
        usuario=actor,
        comentario=comentario or "",
    )


def registrar_cambio_estatus_tramite(
    tramite: models.TramiteCaso,
    usuario,
    estatus_anterior: models.EstatusTramite | None,
    estatus_nuevo: models.EstatusTramite | None,
    comentario: str = "",
) -> None:
    """Guarda el historial cuando cambia el estatus de un trámite asociado."""
    actor = usuario if getattr(usuario, "is_authenticated", False) else None
    models.HistorialEstatusTramiteCaso.objects.create(
        tramite=tramite,
        estatus_anterior=estatus_anterior,
        estatus_nuevo=estatus_nuevo,
        usuario=actor,
        comentario=comentario or "",
    )




class ToolIndexView(LoginRequiredMixin, TemplateView):
    """Índice de herramientas auxiliares."""

    template_name = "tramites/herramientas/index.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["tools"] = [
            {
                "title": "Analizador de requisitos del trámite",
                "description": "Calcula los días válidos de licencias médicas y verifica los 15 años de servicio.",
                "url": reverse_lazy("tramites:analizador-tramite"),
                "badge": "Cálculo",
            }
        ]
        return ctx


class TramiteEligibilityToolView(LoginRequiredMixin, TemplateView):
    """Muestra la herramienta de cálculo de requisitos del trámite."""

    template_name = "tramites/herramientas/analizador_tramite.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "today": timezone.localdate(),
                "minimum_years": 15,
                "regimen_choices": [
                    {"value": "issste", "label": "ISSSTE · 60 días requeridos", "days": 60},
                    {"value": "imss", "label": "IMSS · 90 días requeridos", "days": 90},
                ],
            }
        )
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
        ctx["cct_lookup_url"] = reverse_lazy("tramites:cct-lookup")
        ctx["cct_api_url"] = reverse_lazy("tramites_api:cct-list")
        ctx["prefijos_oficio"] = list(models.PrefijoOficio.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["prefijos_oficio_api_url"] = reverse_lazy("tramites_api:prefijo-oficio-list")
        ctx["tipos_violencia"] = list(models.TipoViolencia.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["tipos_violencia_api_url"] = reverse_lazy("tramites_api:tipo-violencia-list")
        ctx["solicitantes"] = list(models.Solicitante.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["solicitantes_api_url"] = reverse_lazy("tramites_api:solicitante-list")
        ctx["destinatarios"] = list(models.Destinatario.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["destinatarios_api_url"] = reverse_lazy("tramites_api:destinatario-list")
        return ctx


class CasoInternoFormMixin(CCTCatalogContextMixin):
    """Reutiliza el catálogo de CCT en formularios de trámites."""


class CasoInternoListView(LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    """Listado principal de trámites registrados."""

    permission_required = "licencias.view_casointerno"
    model = models.CasoInterno
    paginate_by = 25
    filterset_class = filters.CasoInternoFilter
    template_name = "tramites/tramites/tramites_list.html"
    context_object_name = "casos"
    ordering = "-fecha_apertura"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("cct", "estatus", "tipo_inicial", "area_origen_inicial")
        )


class CasoInternoCreateView(
    CasoInternoFormMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    """Registro de un nuevo trámite."""

    permission_required = "licencias.add_casointerno"
    model = models.CasoInterno
    form_class = forms.CasoInternoForm
    template_name = "tramites/tramites/tramites_form.html"
    success_url = reverse_lazy("tramites:casointerno-list")

    def form_valid(self, form) -> HttpResponse:
        form.instance.creado_por = self.request.user if self.request.user.is_authenticated else None
        response = super().form_valid(form)
        registrar_cambio_estatus_caso(
            caso=self.object,
            usuario=self.request.user,
            estatus_anterior=None,
            estatus_nuevo=self.object.estatus,
        )
        messages.success(self.request, _("Trámite registrado correctamente."))
        return response


class CasoInternoUpdateView(
    CasoInternoFormMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView
):
    """Permite actualizar los datos de un trámite."""

    permission_required = "licencias.change_casointerno"
    model = models.CasoInterno
    form_class = forms.CasoInternoForm
    template_name = "tramites/tramites/tramites_form.html"
    success_url = reverse_lazy("tramites:casointerno-list")

    def form_valid(self, form) -> HttpResponse:
        old_status = self.object.estatus
        response = super().form_valid(form)
        registrar_cambio_estatus_caso(
            caso=self.object,
            usuario=self.request.user,
            estatus_anterior=old_status,
            estatus_nuevo=self.object.estatus,
        )
        messages.success(self.request, _("Trámite actualizado."))
        return response

    def get_success_url(self):
        return self.request.GET.get("from_list") or str(self.success_url)


class CasoInternoDetailView(
    CasoInternoFormMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView
):
    """Detalle de un trámite registrado."""

    permission_required = "licencias.view_casointerno"
    model = models.CasoInterno
    template_name = "tramites/tramites/tramites_detail.html"
    context_object_name = "caso"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["historial_estatus"] = self.object.historial_estatus.select_related(
            "estatus_anterior", "estatus_nuevo", "usuario"
        )
        ctx["tramites_caso"] = (
            self.object.tramites_relacionados.select_related("tipo", "estatus").order_by("-fecha")
        )
        ctx["tramite_caso_form"] = forms.TramiteCasoForm(prefix="tramite_caso")
        ctx["estatus_tramite_form"] = forms.HistorialEstatusTramiteCasoForm()
        ctx["estatus_caso_form"] = forms.HistorialEstatusCasoForm()
        ctx["prefijos_oficio"] = list(models.PrefijoOficio.objects.filter(esta_activo=True).order_by("nombre"))
        return ctx


class TramiteCasoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Permite agregar trámites adicionales a un caso."""

    permission_required = "licencias.add_tramitecaso"
    model = models.TramiteCaso
    form_class = forms.TramiteCasoForm
    template_name = "tramites/tramites/tramite_caso_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("caso_pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["prefix"] = "tramite_caso"
        return kwargs

    def form_valid(self, form):
        form.instance.caso = self.caso
        response = super().form_valid(form)
        registrar_cambio_estatus_tramite(
            tramite=self.object,
            usuario=self.request.user,
            estatus_anterior=None,
            estatus_nuevo=self.object.estatus,
            comentario=self.request.POST.get("comentario_estatus", ""),
        )
        messages.success(self.request, _("Trámite agregado al caso."))
        return response

    def get_success_url(self):
        return reverse_lazy("tramites:casointerno-detail", kwargs={"pk": self.caso.pk})

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["caso"] = self.caso
        ctx["prefijos_oficio"] = list(models.PrefijoOficio.objects.filter(esta_activo=True).order_by("nombre"))
        return ctx


class TramiteCasoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalle de un trámite asociado a un caso."""

    permission_required = "licencias.view_tramitecaso"
    model = models.TramiteCaso
    template_name = "tramites/tramites/tramite_caso_detail.html"
    context_object_name = "tramite"

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("caso", "tipo", "estatus", "solicitante", "dirigido_a", "tipo_violencia")
        )
        caso_pk = self.kwargs.get("caso_pk")
        if caso_pk:
            qs = qs.filter(caso_id=caso_pk)
        return qs

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["historial_estatus"] = self.object.historial_estatus.select_related(
            "estatus_anterior", "estatus_nuevo", "usuario"
        )
        ctx["estatus_tramite_form"] = forms.HistorialEstatusTramiteCasoForm()
        return ctx


class TramiteCasoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Permite editar un trámite asociado a un caso."""

    permission_required = "licencias.change_tramitecaso"
    model = models.TramiteCaso
    form_class = forms.TramiteCasoForm
    template_name = "tramites/tramites/tramite_caso_form.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("caso")
        caso_pk = self.kwargs.get("caso_pk")
        if caso_pk:
            qs = qs.filter(caso_id=caso_pk)
        return qs

    def form_valid(self, form):
        old_status = self.object.estatus
        response = super().form_valid(form)
        registrar_cambio_estatus_tramite(
            tramite=self.object,
            usuario=self.request.user,
            estatus_anterior=old_status,
            estatus_nuevo=self.object.estatus,
            comentario=self.request.POST.get("comentario_estatus", ""),
        )
        messages.success(self.request, _("Trámite actualizado."))
        return response

    def get_success_url(self):
        return reverse_lazy(
            "tramites:tramite-caso-detail",
            kwargs={"caso_pk": self.object.caso_id, "pk": self.object.pk},
        )

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["caso"] = self.object.caso
        ctx["prefijos_oficio"] = list(models.PrefijoOficio.objects.filter(esta_activo=True).order_by("nombre"))
        return ctx


class TramiteCasoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Elimina un trámite asociado a un caso previa confirmación."""

    permission_required = "licencias.delete_tramitecaso"
    model = models.TramiteCaso
    template_name = "tramites/tramites/tramite_caso_confirm_delete.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("caso")
        caso_pk = self.kwargs.get("caso_pk")
        if caso_pk:
            qs = qs.filter(caso_id=caso_pk)
        return qs

    def get_success_url(self):
        return reverse_lazy("tramites:casointerno-detail", kwargs={"pk": self.object.caso_id})

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        messages.success(request, _("Trámite eliminado."))
        return super().delete(request, *args, **kwargs)


class TramiteCasoEstatusCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Agrega un cambio de estatus a un trámite y actualiza el estatus actual."""

    permission_required = "licencias.change_tramitecaso"
    form_class = forms.HistorialEstatusTramiteCasoForm

    def dispatch(self, request, *args, **kwargs):
        self.tramite = get_object_or_404(
            models.TramiteCaso.objects.select_related("caso", "estatus"), pk=kwargs.get("tramite_pk")
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        nuevo_estatus = form.cleaned_data["estatus_nuevo"]
        comentario = form.cleaned_data.get("comentario", "")
        anterior = (
            self.tramite.historial_estatus.order_by("-fecha_cambio", "-id")
            .values_list("estatus_nuevo", flat=True)
            .first()
        )
        estatus_anterior_obj = None
        if anterior:
            try:
                estatus_anterior_obj = models.EstatusTramite.objects.get(pk=anterior)
            except models.EstatusTramite.DoesNotExist:
                estatus_anterior_obj = self.tramite.estatus
        else:
            estatus_anterior_obj = self.tramite.estatus
        registrar_cambio_estatus_tramite(
            tramite=self.tramite,
            usuario=self.request.user,
            estatus_anterior=estatus_anterior_obj,
            estatus_nuevo=nuevo_estatus,
            comentario=comentario,
        )
        self.tramite.estatus = nuevo_estatus
        self.tramite.save(update_fields=["estatus", "actualizado_en"])
        messages.success(self.request, _("Estatus del trámite actualizado."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "tramites:tramite-caso-detail",
            kwargs={"caso_pk": self.tramite.caso_id, "pk": self.tramite.pk},
        )

    def form_invalid(self, form):
        messages.error(self.request, _("No se pudo registrar el cambio de estatus."))
        return redirect(
            "tramites:tramite-caso-detail",
            caso_pk=self.tramite.caso_id,
            pk=self.tramite.pk,
        )


class TramiteCasoEstatusUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edita el último cambio de estatus de un trámite."""

    permission_required = "licencias.change_tramitecaso"
    model = models.HistorialEstatusTramiteCaso
    form_class = forms.HistorialEstatusTramiteCasoForm
    template_name = "tramites/tramites/tramite_caso_status_form.html"
    context_object_name = "estatus_tramite"

    def get_queryset(self):
        return super().get_queryset().select_related("tramite", "estatus_anterior", "estatus_nuevo")

    def dispatch(self, request, *args, **kwargs):
        self.tramite = get_object_or_404(models.TramiteCaso, pk=kwargs.get("tramite_pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        ultimo = obj.tramite.historial_estatus.order_by("-fecha_cambio", "-id").first()
        if ultimo and ultimo.pk != obj.pk:
            messages.error(
                self.request,
                _("Solo puedes editar el último cambio de estatus para mantener la consistencia."),
            )
            raise Http404
        return obj

    def form_valid(self, form):
        response = super().form_valid(form)
        self.tramite.estatus = form.cleaned_data["estatus_nuevo"]
        self.tramite.save(update_fields=["estatus", "actualizado_en"])
        messages.success(self.request, _("Cambio de estatus actualizado."))
        return response

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["tramite"] = self.tramite
        return ctx

    def get_success_url(self):
        return reverse_lazy(
            "tramites:tramite-caso-detail",
            kwargs={"caso_pk": self.tramite.caso_id, "pk": self.tramite.pk},
        )


class TramiteCasoEstatusDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Elimina el último cambio de estatus de un trámite y revierte el estatus si aplica."""

    permission_required = "licencias.change_tramitecaso"
    model = models.HistorialEstatusTramiteCaso
    template_name = "tramites/tramites/tramite_caso_status_confirm_delete.html"
    context_object_name = "estatus_tramite"

    def get_queryset(self):
        return super().get_queryset().select_related("tramite", "estatus_anterior", "estatus_nuevo")

    def dispatch(self, request, *args, **kwargs):
        self.tramite = get_object_or_404(models.TramiteCaso, pk=kwargs.get("tramite_pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        ultimo = obj.tramite.historial_estatus.order_by("-fecha_cambio", "-id").first()
        if ultimo and ultimo.pk != obj.pk:
            messages.error(
                self.request,
                _("Solo puedes eliminar el último cambio de estatus para mantener la consistencia."),
            )
            raise Http404
        return obj

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        obj = self.get_object()
        response = super().delete(request, *args, **kwargs)
        nuevo_estatus = obj.estatus_anterior
        self.tramite.estatus = nuevo_estatus
        self.tramite.save(update_fields=["estatus", "actualizado_en"])
        messages.success(request, _("Cambio de estatus eliminado y estatus del trámite actualizado."))
        return response

    def get_success_url(self):
        return reverse_lazy(
            "tramites:tramite-caso-detail",
            kwargs={"caso_pk": self.tramite.caso_id, "pk": self.tramite.pk},
        )

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["tramite"] = self.tramite
        return ctx


class CasoInternoDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, DeleteView
):
    """Elimina un trámite previa confirmación."""

    permission_required = "licencias.delete_casointerno"
    model = models.CasoInterno
    template_name = "tramites/tramites/tramites_confirm_delete.html"
    success_url = reverse_lazy("tramites:casointerno-list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        messages.success(request, _("Trámite eliminado."))
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return self.request.GET.get("from_list") or str(self.success_url)


class CasoInternoEstatusCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Agrega un cambio de estatus al trámite principal y actualiza su estatus actual."""

    permission_required = "licencias.change_casointerno"
    form_class = forms.HistorialEstatusCasoForm

    def dispatch(self, request, *args, **kwargs):
        self.caso = get_object_or_404(models.CasoInterno.objects.select_related("estatus"), pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        nuevo_estatus = form.cleaned_data["estatus_nuevo"]
        comentario = form.cleaned_data.get("comentario", "")
        anterior = (
            self.caso.historial_estatus.order_by("-fecha_cambio", "-id")
            .values_list("estatus_nuevo", flat=True)
            .first()
        )
        estatus_anterior_obj = None
        if anterior:
            try:
                estatus_anterior_obj = models.EstatusCaso.objects.get(pk=anterior)
            except models.EstatusCaso.DoesNotExist:
                estatus_anterior_obj = self.caso.estatus
        else:
            estatus_anterior_obj = self.caso.estatus
        registrar_cambio_estatus_caso(
            caso=self.caso,
            usuario=self.request.user,
            estatus_anterior=estatus_anterior_obj,
            estatus_nuevo=nuevo_estatus,
            comentario=comentario,
        )
        self.caso.estatus = nuevo_estatus
        self.caso.save(update_fields=["estatus", "actualizado_en"])
        messages.success(self.request, _("Estatus del trámite actualizado."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("No se pudo registrar el cambio de estatus."))
        return redirect("tramites:casointerno-detail", pk=self.caso.pk)

    def get_success_url(self):
        return reverse_lazy("tramites:casointerno-detail", kwargs={"pk": self.caso.pk})


class CasoInternoEstatusUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Permite editar el último cambio de estatus del trámite principal."""

    permission_required = "licencias.change_casointerno"
    model = models.HistorialEstatusCaso
    form_class = forms.HistorialEstatusCasoForm
    template_name = "tramites/tramites/caso_estatus_form.html"
    context_object_name = "estatus_caso"

    def get_queryset(self):
        return super().get_queryset().select_related("caso", "estatus_anterior", "estatus_nuevo")

    def dispatch(self, request, *args, **kwargs):
        self.caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("pk"))
        self.estatus_pk = kwargs.get("estatus_pk")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        qs = queryset or self.get_queryset()
        obj = get_object_or_404(qs, pk=self.estatus_pk)
        ultimo = obj.caso.historial_estatus.order_by("-fecha_cambio", "-id").first()
        if ultimo and ultimo.pk != obj.pk:
            messages.error(
                self.request,
                _("Solo puedes editar el último cambio de estatus para mantener la consistencia."),
            )
            raise Http404
        return obj

    def form_valid(self, form):
        response = super().form_valid(form)
        self.caso.estatus = form.cleaned_data["estatus_nuevo"]
        self.caso.save(update_fields=["estatus", "actualizado_en"])
        messages.success(self.request, _("Cambio de estatus actualizado."))
        return response

    def get_success_url(self):
        return reverse_lazy("tramites:casointerno-detail", kwargs={"pk": self.caso.pk})

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["caso"] = self.caso
        return ctx


class CasoInternoEstatusDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Elimina el último cambio de estatus del trámite principal y revierte el estatus si aplica."""

    permission_required = "licencias.change_casointerno"
    model = models.HistorialEstatusCaso
    template_name = "tramites/tramites/caso_estatus_confirm_delete.html"
    context_object_name = "estatus_caso"

    def get_queryset(self):
        return super().get_queryset().select_related("caso", "estatus_anterior", "estatus_nuevo")

    def dispatch(self, request, *args, **kwargs):
        self.caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("pk"))
        self.estatus_pk = kwargs.get("estatus_pk")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        qs = queryset or self.get_queryset()
        obj = get_object_or_404(qs, pk=self.estatus_pk)
        ultimo = obj.caso.historial_estatus.order_by("-fecha_cambio", "-id").first()
        if ultimo and ultimo.pk != obj.pk:
            messages.error(
                self.request,
                _("Solo puedes eliminar el último cambio de estatus para mantener la consistencia."),
            )
            raise Http404
        return obj

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        obj = self.get_object()
        response = super().delete(request, *args, **kwargs)
        self.caso.estatus = obj.estatus_anterior
        self.caso.save(update_fields=["estatus", "actualizado_en"])
        messages.success(request, _("Cambio de estatus eliminado y estatus del trámite actualizado."))
        return response

    def get_success_url(self):
        return reverse_lazy("tramites:casointerno-detail", kwargs={"pk": self.caso.pk})

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["caso"] = self.caso
        return ctx


class CCTLookupView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Devuelve información del CCT desde el catálogo de secundarias."""

    permission_required = "licencias.add_casointerno"

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
            raise PermissionDenied("No tienes permisos para crear CCT.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_cctsecundaria"):
            raise PermissionDenied("No tienes permisos para editar CCT.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_cctsecundaria"):
            raise PermissionDenied("No tienes permisos para eliminar CCT.")
        instance.delete()


class TipoProcesoViewSet(viewsets.ModelViewSet):
    """API para gestionar tipos de trámite."""

    queryset = models.TipoProceso.objects.order_by("nombre")
    serializer_class = serializers.TipoProcesoSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_tipoproceso"):
            raise PermissionDenied("No tienes permisos para crear tipos de trámite.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_tipoproceso"):
            raise PermissionDenied("No tienes permisos para editar tipos de trámite.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_tipoproceso"):
            raise PermissionDenied("No tienes permisos para eliminar tipos de trámite.")
        instance.delete()


class EstatusCasoViewSet(viewsets.ModelViewSet):
    """API para gestionar estatus de caso."""

    queryset = models.EstatusCaso.objects.order_by("orden", "nombre")
    serializer_class = serializers.EstatusCasoSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre",)
    ordering_fields = ("nombre", "orden", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_estatuscaso"):
            raise PermissionDenied("No tienes permisos para crear estatus de caso.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_estatuscaso"):
            raise PermissionDenied("No tienes permisos para editar estatus de caso.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_estatuscaso"):
            raise PermissionDenied("No tienes permisos para eliminar estatus de caso.")
        try:
            instance.delete()
        except dj_models.ProtectedError as exc:
            raise PermissionDenied(
                "No se puede eliminar el estatus porque está en uso en trámites o en su historial."
            ) from exc


class TipoViolenciaViewSet(viewsets.ModelViewSet):
    """API para gestionar tipos de violencia (opcional en el trámite)."""

    queryset = models.TipoViolencia.objects.order_by("nombre")
    serializer_class = serializers.TipoViolenciaSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_tipoviolencia"):
            raise PermissionDenied("No tienes permisos para crear tipos de violencia.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_tipoviolencia"):
            raise PermissionDenied("No tienes permisos para editar tipos de violencia.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_tipoviolencia"):
            raise PermissionDenied("No tienes permisos para eliminar tipos de violencia.")
        instance.delete()


class PrefijoOficioViewSet(viewsets.ModelViewSet):
    """API para gestionar prefijos sugeridos del número de oficio."""

    queryset = models.PrefijoOficio.objects.order_by("nombre")
    serializer_class = serializers.PrefijoOficioSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_prefijooficio"):
            raise PermissionDenied("No tienes permisos para crear prefijos de oficio.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_prefijooficio"):
            raise PermissionDenied("No tienes permisos para editar prefijos de oficio.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_prefijooficio"):
            raise PermissionDenied("No tienes permisos para eliminar prefijos de oficio.")
        instance.delete()


class SolicitanteViewSet(viewsets.ModelViewSet):
    """API para gestionar solicitantes."""

    queryset = models.Solicitante.objects.order_by("nombre")
    serializer_class = serializers.SolicitanteSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_solicitante"):
            raise PermissionDenied("No tienes permisos para crear solicitantes.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_solicitante"):
            raise PermissionDenied("No tienes permisos para editar solicitantes.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_solicitante"):
            raise PermissionDenied("No tienes permisos para eliminar solicitantes.")
        instance.delete()


class DestinatarioViewSet(viewsets.ModelViewSet):
    """API para gestionar destinatarios (dirigido a)."""

    queryset = models.Destinatario.objects.order_by("nombre")
    serializer_class = serializers.DestinatarioSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_destinatario"):
            raise PermissionDenied("No tienes permisos para crear destinatarios.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_destinatario"):
            raise PermissionDenied("No tienes permisos para editar destinatarios.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_destinatario"):
            raise PermissionDenied("No tienes permisos para eliminar destinatarios.")
        instance.delete()


class TramiteCasoViewSet(viewsets.ModelViewSet):
    """API para gestionar trámites adicionales de un caso."""

    queryset = models.TramiteCaso.objects.select_related("caso", "tipo", "estatus").order_by("-fecha", "-creado_en")
    serializer_class = serializers.TramiteCasoSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("asunto", "numero_oficio", "observaciones")
    ordering_fields = ("fecha", "creado_en")

    def get_queryset(self):
        qs = super().get_queryset()
        caso_id = self.request.query_params.get("caso")
        if caso_id:
            qs = qs.filter(caso_id=caso_id)
        return qs

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_tramitecaso"):
            raise PermissionDenied("No tienes permisos para crear trámites del caso.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_tramitecaso"):
            raise PermissionDenied("No tienes permisos para editar trámites del caso.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_tramitecaso"):
            raise PermissionDenied("No tienes permisos para eliminar trámites del caso.")
        instance.delete()


class EstatusTramiteViewSet(viewsets.ModelViewSet):
    """API para gestionar estatus de trámites asociados a casos."""

    queryset = models.EstatusTramite.objects.order_by("orden", "nombre")
    serializer_class = serializers.EstatusTramiteSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre",)
    ordering_fields = ("nombre", "orden", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_estatustramite"):
            raise PermissionDenied("No tienes permisos para crear estatus de trámite.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_estatustramite"):
            raise PermissionDenied("No tienes permisos para editar estatus de trámite.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_estatustramite"):
            raise PermissionDenied("No tienes permisos para eliminar estatus de trámite.")
        instance.delete()
