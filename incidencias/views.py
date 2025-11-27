"""Vistas del módulo de incidencias y reporteador."""
from __future__ import annotations

from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from incidencias import forms, models


def get_plantilla() -> models.PlantillaReporteIncidencia:
    plantilla = models.PlantillaReporteIncidencia.objects.first()
    if plantilla:
        return plantilla
    return models.PlantillaReporteIncidencia.objects.create()


def resolver_cuerpo(incidencia: models.Incidencia, plantilla: models.PlantillaReporteIncidencia) -> str:
    if incidencia.cuerpo_personalizado:
        return incidencia.cuerpo_personalizado
    return plantilla.render_cuerpo(incidencia)


def get_weasyprint_html():  # pragma: no cover - import diferido
    try:
        from weasyprint import HTML
    except Exception:
        return None
    return HTML


class IncidenciaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listado simple para ubicar incidencias capturadas."""

    permission_required = "incidencias.view_incidencia"
    model = models.Incidencia
    template_name = "incidencias/incidencia_list.html"
    context_object_name = "incidencias"
    paginate_by = 25
    ordering = "-creado_en"


class IncidenciaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Captura inicial de la incidencia."""

    permission_required = "incidencias.add_incidencia"
    model = models.Incidencia
    form_class = forms.IncidenciaForm
    template_name = "incidencias/incidencia_form.html"
    def form_valid(self, form: forms.IncidenciaForm) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, _("Incidencia registrada. Ahora puedes editar el reporte."))
        return response

    def get_success_url(self) -> str:
        return reverse("incidencias:incidencia-reporte-editar", args=[self.object.pk])


class IncidenciaReporteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Previsualización y edición del cuerpo antes de generar PDF."""

    permission_required = "incidencias.change_incidencia"
    model = models.Incidencia
    form_class = forms.IncidenciaReporteForm
    template_name = "incidencias/incidencia_reporte_preview.html"

    def get_initial(self) -> Dict[str, Any]:
        initial = super().get_initial()
        incidencia: models.Incidencia = self.get_object()
        if not incidencia.cuerpo_personalizado:
            plantilla = get_plantilla()
            initial["cuerpo_personalizado"] = resolver_cuerpo(incidencia, plantilla)
        return initial

    def form_valid(self, form: forms.IncidenciaReporteForm) -> HttpResponse:
        messages.success(self.request, _("Cuerpo del reporte actualizado."))
        response = super().form_valid(form)
        return response

    def get_success_url(self) -> str:
        return reverse("incidencias:incidencia-reporte-editar", args=[self.object.pk])

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        plantilla = get_plantilla()
        incidencia: models.Incidencia = self.object
        ctx.update(
            {
                "plantilla": plantilla,
                "cuerpo_resuelto": resolver_cuerpo(incidencia, plantilla),
                "tabla_datos": [
                    ("C.C.T", incidencia.cct),
                    ("No. serie", incidencia.numero_serie or "—"),
                    ("Días", incidencia.dias),
                    ("Del", date_format(incidencia.fecha_del, "DATE_FORMAT")),
                    ("Al", date_format(incidencia.fecha_al, "DATE_FORMAT")),
                ],
            }
        )
        return ctx

class IncidenciaReportePDFView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Genera el PDF listo para imprimir."""

    permission_required = "incidencias.view_incidencia"

    def get(self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any) -> HttpResponse:
        incidencia = get_object_or_404(models.Incidencia, pk=pk)
        plantilla = get_plantilla()
        cuerpo = resolver_cuerpo(incidencia, plantilla)
        context = {
            "incidencia": incidencia,
            "plantilla": plantilla,
            "cuerpo_resuelto": cuerpo,
        }
        template = get_template("incidencias/incidencia_reporte_pdf.html")
        html_string = template.render(context)
        html_renderer = get_weasyprint_html()
        if html_renderer is None:
            raise Http404("WeasyPrint no está disponible en el servidor.")
        pdf_file = html_renderer(
            string=html_string, base_url=request.build_absolute_uri("/")
        ).write_pdf()
        response = HttpResponse(pdf_file, content_type="application/pdf")
        response["Content-Disposition"] = f'filename="reporte_incidencia_{incidencia.numero}.pdf"'
        return response
