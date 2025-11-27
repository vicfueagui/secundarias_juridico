from django.contrib import admin

from incidencias import models


@admin.register(models.Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre_completo", "cct", "dias", "fecha_del", "fecha_al")
    search_fields = ("numero", "apellido_paterno", "apellido_materno", "nombres", "rfc", "cct")
    list_filter = ("fecha_del", "fecha_al")


@admin.register(models.PlantillaReporteIncidencia)
class PlantillaReporteIncidenciaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "titulo", "actualizado_en")
