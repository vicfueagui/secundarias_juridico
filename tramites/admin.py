"""Configuración del administrador para el módulo de trámites."""
from __future__ import annotations

from django.contrib import admin

from tramites import models


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


@admin.register(models.TipoProceso)
class TipoProcesoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "es_documento", "esta_activo", "actualizado_en")
    list_filter = ("es_documento", "esta_activo")
    search_fields = ("nombre", "descripcion")
    list_editable = ("es_documento", "esta_activo")


@admin.register(models.AreaProceso)
class AreaProcesoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "siglas", "esta_activo", "actualizado_en")
    list_filter = ("esta_activo",)
    search_fields = ("nombre", "siglas")
    list_editable = ("esta_activo",)


@admin.register(models.EstatusCaso)
class EstatusCasoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "esta_activo")
    list_editable = ("orden", "esta_activo")
    search_fields = ("nombre",)
    ordering = ("orden",)


@admin.register(models.CasoInterno)
class CasoInternoAdmin(admin.ModelAdmin):
    date_hierarchy = "fecha_apertura"
    list_display = (
        "cct",
        "descripcion_breve",
        "tipo_inicial",
        "folio_inicial",
        "estatus",
        "fecha_apertura",
        "creado_por",
    )
    list_filter = (
        "estatus",
        "tipo_inicial",
        "area_origen_inicial",
        ("fecha_apertura", admin.DateFieldListFilter),
    )
    search_fields = (
        "descripcion_breve",
        "folio_inicial",
        "cct__cct",
        "cct_nombre",
    )
    autocomplete_fields = ("cct", "estatus", "tipo_inicial", "area_origen_inicial")
    readonly_fields = ("fecha_registro", "actualizado_en")
