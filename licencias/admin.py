"""Configuración del administrador de Django."""
from __future__ import annotations

import csv
from datetime import datetime
from typing import Iterable

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from licencias import models
from licencias.services import validators


@admin.register(
    models.Subsistema,
    models.TipoTramite,
    models.Etapa,
    models.Sindicato,
    models.Diagnostico,
    models.Area,
    models.Resultado,
)
class CatalogoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "esta_activo", "actualizado_en")
    list_editable = ("esta_activo",)
    search_fields = ("nombre",)
    list_filter = ("esta_activo",)
    ordering = ("nombre",)


class OficioInline(admin.TabularInline):
    model = models.Oficio
    extra = 0
    fields = ("tipo", "numero", "fecha", "area_emisora", "observaciones")
    autocomplete_fields = ("area_emisora",)


class NotificacionInline(admin.TabularInline):
    model = models.Notificacion
    extra = 0
    fields = ("destinatario", "numero_oficio", "fecha", "observaciones")


@admin.register(models.Tramite)
class TramiteAdmin(admin.ModelAdmin):
    date_hierarchy = "fecha_recepcion_nivel"
    list_display = (
        "folio",
        "tipo_tramite",
        "subsistema",
        "trabajador_nombre",
        "estado_actual",
        "fecha_recepcion_nivel",
        "user_responsable",
    )
    search_fields = (
        "folio",
        "trabajador_nombre",
        "oficio_origen_num",
        "persona_tramita",
    )
    list_filter = (
        "tipo_tramite",
        "subsistema",
        "estado_actual",
        "sindicato",
        "resultado_resolucion",
        ("fecha_recepcion_nivel", admin.DateFieldListFilter),
    )
    autocomplete_fields = (
        "tipo_tramite",
        "subsistema",
        "diagnostico",
        "sindicato",
        "resultado_resolucion",
        "estado_actual",
        "user_responsable",
    )
    readonly_fields = ("folio", "created_at", "updated_at")
    inlines = [OficioInline, NotificacionInline]
    actions = ("accion_asignarme", "accion_marcar_cierre", "accion_exportar_csv")

    def accion_asignarme(self, request, queryset: Iterable[models.Tramite]) -> None:
        updated = queryset.update(user_responsable=request.user)
        self.message_user(
            request,
            f"Se asignaron {updated} trámites a {request.user}.",
            messages.SUCCESS,
        )

    accion_asignarme.short_description = "Asignarme como responsable"

    def accion_marcar_cierre(self, request, queryset: Iterable[models.Tramite]) -> None:
        etapa_cierre = (
            models.Etapa.objects.filter(
                nombre__icontains="cierre", esta_activo=True
            ).first()
        )
        if not etapa_cierre:
            self.message_user(
                request,
                "No existe una etapa con nombre similar a 'Cierre'.",
                messages.ERROR,
            )
            return

        actualizados = 0
        for tramite in queryset:
            try:
                validators.validar_transicion_etapa(tramite.estado_actual, etapa_cierre)
            except ValidationError as exc:
                self.message_user(
                    request, f"{tramite.folio}: {exc}", level=messages.WARNING
                )
                continue
            tramite.estado_actual = etapa_cierre
            try:
                tramite.save()
            except ValidationError as exc:
                self.message_user(
                    request,
                    f"{tramite.folio}: {exc}",
                    level=messages.ERROR,
                )
                continue
            actualizados += 1

        self.message_user(
            request, f"Se movieron {actualizados} trámites a Cierre.", messages.SUCCESS
        )

    accion_marcar_cierre.short_description = "Mover a etapa Cierre"

    def accion_exportar_csv(
        self, request, queryset: Iterable[models.Tramite]
    ) -> HttpResponse:
        filename = f"tramites_{datetime.now():%Y%m%d_%H%M%S}.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "Folio",
                "Tipo trámite",
                "Subsistema",
                "Trabajador",
                "Estado",
                "Fecha recepción nivel",
                "Resultado resolución",
            ]
        )
        for tramite in queryset:
            writer.writerow(
                [
                    tramite.folio,
                    tramite.tipo_tramite.nombre,
                    tramite.subsistema.nombre,
                    tramite.trabajador_nombre,
                    tramite.estado_actual.nombre,
                    tramite.fecha_recepcion_nivel,
                    tramite.resultado_resolucion.nombre
                    if tramite.resultado_resolucion
                    else "",
                ]
        )
        return response

    accion_exportar_csv.short_description = "Exportar selección a CSV"


@admin.register(models.Oficio)
class OficioAdmin(admin.ModelAdmin):
    list_display = ("tramite", "tipo", "numero", "fecha", "area_emisora")
    list_filter = ("tipo", "area_emisora")
    search_fields = ("tramite__folio", "numero")
    autocomplete_fields = ("tramite", "area_emisora")


@admin.register(models.Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("tramite", "destinatario", "numero_oficio", "fecha")
    list_filter = ("destinatario",)
    search_fields = ("tramite__folio", "numero_oficio")
    autocomplete_fields = ("tramite",)


@admin.register(models.Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ("tramite", "etapa_anterior", "etapa_nueva", "fecha", "usuario")
    list_filter = ("etapa_nueva", "usuario")
    autocomplete_fields = ("tramite", "etapa_anterior", "etapa_nueva", "usuario")
    date_hierarchy = "fecha"


@admin.register(models.CCTSecundaria)
class CCTSecundariaAdmin(admin.ModelAdmin):
    list_display = (
        "cct",
        "nombre",
        "asesor",
        "sostenimiento",
        "servicio",
        "municipio",
        "turno",
        "actualizado_en",
    )
    search_fields = ("cct", "nombre", "asesor", "sostenimiento", "servicio", "municipio")
    list_filter = ("municipio", "turno")
    ordering = ("cct",)


@admin.register(models.ControlInterno)
class ControlInternoAdmin(admin.ModelAdmin):
    date_hierarchy = "fecha_memorandum"
    list_display = (
        "numero_interno",
        "memorandum",
        "cct",
        "cct_nombre",
        "sostenimiento_c_subcontrol",
        "estatus",
        "fecha_memorandum",
        "fecha_contestacion",
    )
    list_filter = ("estatus", "anio", "asesor")
    search_fields = (
        "numero_interno",
        "memorandum",
        "asunto",
        "cct__cct",
        "cct_nombre",
        "sostenimiento_c_subcontrol",
    )
    autocomplete_fields = ("cct",)
    readonly_fields = ("creado_en", "actualizado_en")


@admin.register(models.RelacionProtocolo)
class RelacionProtocoloAdmin(admin.ModelAdmin):
    date_hierarchy = "fecha_inicio"
    list_display = (
        "numero_registro",
        "cct",
        "nombre_nna",
        "tipo_violencia",
        "estatus",
        "anio",
        "actualizado_en",
    )
    list_filter = ("estatus", "anio", "sexo")
    search_fields = (
        "numero_registro",
        "nombre_nna",
        "iniciales",
        "cct__cct",
        "cct__nombre",
        "tipo_violencia",
    )
    autocomplete_fields = ("cct",)
