"""Configuración del administrador para el módulo de trámites."""
from __future__ import annotations

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, Permission
from django import forms
from django.utils.translation import gettext_lazy as _

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


@admin.register(models.PlantillaCentroTrabajo)
class PlantillaCentroTrabajoAdmin(admin.ModelAdmin):
    list_display = (
        "cct",
        "nombre",
        "municipio",
        "asesor",
        "sostenimiento",
        "subnivel",
        "turno",
        "actualizado_en",
    )
    search_fields = ("cct", "nombre", "municipio", "asesor", "sostenimiento", "subnivel")
    list_filter = ("municipio", "turno", "sostenimiento", "subnivel")
    ordering = ("cct",)


@admin.register(models.PlantillaEmpleado)
class PlantillaEmpleadoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rfc", "curp", "correo", "telefono", "celular", "actualizado_en")
    search_fields = ("nombre", "rfc", "curp", "correo", "telefono", "celular")
    ordering = ("nombre",)


@admin.register(models.PlantillaRegistro)
class PlantillaRegistroAdmin(admin.ModelAdmin):
    list_display = ("origen_id", "empleado", "centro_trabajo", "ciclo", "anio", "situacion")
    search_fields = ("empleado__nombre", "empleado__rfc", "empleado__curp", "centro_trabajo__cct")
    list_filter = ("anio", "ciclo", "situacion", "funcion")
    autocomplete_fields = ("empleado", "centro_trabajo")
    ordering = ("-anio", "-ciclo")


@admin.register(models.PlantillaClavePresupuestal)
class PlantillaClavePresupuestalAdmin(admin.ModelAdmin):
    list_display = ("clave", "registro")
    search_fields = ("clave", "registro__empleado__nombre", "registro__centro_trabajo__cct")
    autocomplete_fields = ("registro",)


@admin.register(models.CasoTrabajador)
class CasoTrabajadorAdmin(admin.ModelAdmin):
    list_display = (
        "caso",
        "trabajador",
        "es_principal",
        "centro_trabajo_preferido",
        "actualizado_en",
    )
    search_fields = (
        "caso__id",
        "trabajador__nombre",
        "trabajador__rfc",
        "trabajador__curp",
        "centro_trabajo_preferido__cct",
    )
    list_filter = ("es_principal",)


@admin.register(models.TipoProceso)
class TipoProcesoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "es_documento", "esta_activo", "actualizado_en")
    list_filter = ("es_documento", "esta_activo")
    search_fields = ("nombre", "descripcion")
    list_editable = ("es_documento", "esta_activo")


@admin.register(models.PlantillaCapturaTipo)
class PlantillaCapturaTipoAdmin(admin.ModelAdmin):
    list_display = (
        "tipo_proceso",
        "ambito",
        "nombre",
        "esta_activa",
        "orden",
        "actualizado_en",
    )
    list_filter = ("ambito", "esta_activa")
    search_fields = ("nombre", "descripcion", "tipo_proceso__nombre")
    autocomplete_fields = ("tipo_proceso",)


@admin.register(models.SLARegla)
class SLAReglaAdmin(admin.ModelAdmin):
    list_display = (
        "ambito",
        "tipo_proceso",
        "estatus_caso",
        "estatus_tramite",
        "dias_objetivo",
        "dias_alerta_amarilla",
        "dias_escalamiento",
        "peso_riesgo",
        "grupo_escalamiento",
        "esta_activa",
    )
    list_filter = ("ambito", "esta_activa", "grupo_escalamiento")
    search_fields = (
        "nombre",
        "tipo_proceso__nombre",
        "estatus_caso__nombre",
        "estatus_tramite__nombre",
    )
    autocomplete_fields = ("tipo_proceso", "estatus_caso", "estatus_tramite", "grupo_escalamiento")
    ordering = ("ambito", "tipo_proceso__nombre", "orden", "id")


@admin.register(models.SLAAlertaRegistro)
class SLAAlertaRegistroAdmin(admin.ModelAdmin):
    list_display = (
        "tipo_alerta",
        "caso",
        "tramite",
        "regla",
        "fecha_vencimiento",
        "dias_restantes",
        "creado_en",
    )
    list_filter = ("tipo_alerta", ("creado_en", admin.DateFieldListFilter))
    search_fields = (
        "caso__numero_oficio",
        "tramite__numero_oficio",
        "metadata",
    )
    autocomplete_fields = ("caso", "tramite", "regla", "async_job")
    readonly_fields = ("creado_en",)


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


@admin.register(models.EstatusTramite)
class EstatusTramiteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "esta_activo")
    list_editable = ("orden", "esta_activo")
    search_fields = ("nombre",)
    ordering = ("orden",)


@admin.register(models.TipoViolencia)
class TipoViolenciaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "esta_activo")
    list_editable = ("esta_activo",)
    search_fields = ("nombre", "descripcion")


@admin.register(models.PrefijoOficio)
class PrefijoOficioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "esta_activo")
    list_editable = ("esta_activo",)
    search_fields = ("nombre", "descripcion")


@admin.register(models.EstatusLicencia)
class EstatusLicenciaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "esta_activo")
    list_editable = ("orden", "esta_activo")
    search_fields = ("nombre",)
    ordering = ("orden",)


@admin.register(models.Solicitante)
class SolicitanteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "esta_activo")
    list_editable = ("esta_activo",)
    search_fields = ("nombre", "descripcion")


@admin.register(models.Destinatario)
class DestinatarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "esta_activo")
    list_editable = ("esta_activo",)
    search_fields = ("nombre", "descripcion")


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


@admin.register(models.HistorialEstatusCaso)
class HistorialEstatusCasoAdmin(admin.ModelAdmin):
    date_hierarchy = "fecha_cambio"
    list_display = (
        "caso",
        "estatus_anterior",
        "estatus_nuevo",
        "fecha_estatus",
        "fecha_cambio",
        "usuario",
    )
    list_filter = (
        "estatus_nuevo",
        ("fecha_estatus", admin.DateFieldListFilter),
        ("fecha_cambio", admin.DateFieldListFilter),
    )
    search_fields = ("caso__cct__cct", "caso__descripcion_breve", "usuario__username")
    autocomplete_fields = ("caso", "estatus_anterior", "estatus_nuevo", "usuario")
    readonly_fields = ("fecha_cambio",)


@admin.register(models.TramiteCaso)
class TramiteCasoAdmin(admin.ModelAdmin):
    date_hierarchy = "fecha"
    list_display = ("caso", "tipo", "estatus", "fecha", "numero_oficio")
    list_filter = (
        "tipo",
        "estatus",
        "tipo_violencia",
        ("fecha", admin.DateFieldListFilter),
    )
    search_fields = (
        "caso__descripcion_breve",
        "caso__cct__cct",
        "numero_oficio",
        "asunto",
    )
    autocomplete_fields = (
        "caso",
        "tipo",
        "estatus",
        "tipo_violencia",
        "solicitante",
        "dirigido_a",
    )
    readonly_fields = ("creado_en", "actualizado_en")


@admin.register(models.HistorialEstatusTramiteCaso)
class HistorialEstatusTramiteCasoAdmin(admin.ModelAdmin):
    date_hierarchy = "fecha_cambio"
    list_display = (
        "tramite",
        "estatus_anterior",
        "estatus_nuevo",
        "fecha_estatus",
        "fecha_cambio",
        "usuario",
    )
    list_filter = (
        "estatus_nuevo",
        ("fecha_estatus", admin.DateFieldListFilter),
        ("fecha_cambio", admin.DateFieldListFilter),
    )
    search_fields = ("tramite__caso__descripcion_breve", "tramite__caso__cct__cct", "usuario__username")
    autocomplete_fields = ("tramite", "estatus_anterior", "estatus_nuevo", "usuario")
    readonly_fields = ("fecha_cambio",)


@admin.register(models.BitacoraCaso)
class BitacoraCasoAdmin(admin.ModelAdmin):
    list_display = (
        "accion",
        "caso_origen",
        "caso_destino",
        "tramite",
        "usuario",
        "creado_en",
    )
    list_filter = ("accion", ("creado_en", admin.DateFieldListFilter))
    search_fields = (
        "detalle",
        "caso_origen__numero_oficio",
        "caso_destino__numero_oficio",
        "tramite__numero_oficio",
        "usuario__username",
    )
    autocomplete_fields = ("caso_origen", "caso_destino", "tramite", "usuario")
    readonly_fields = ("creado_en",)


@admin.register(models.CasoComentarioInterno)
class CasoComentarioInternoAdmin(admin.ModelAdmin):
    date_hierarchy = "creado_en"
    list_display = ("caso", "autor", "creado_en", "actualizado_en")
    search_fields = ("caso__numero_oficio", "caso__descripcion_breve", "mensaje", "autor__username")
    autocomplete_fields = ("caso", "autor", "menciones")
    readonly_fields = ("creado_en", "actualizado_en")


@admin.register(models.CasoTareaInterna)
class CasoTareaInternaAdmin(admin.ModelAdmin):
    date_hierarchy = "fecha_compromiso"
    list_display = (
        "caso",
        "titulo",
        "responsable",
        "fecha_compromiso",
        "estado",
        "creada_por",
        "completada_por",
        "completada_en",
    )
    search_fields = (
        "caso__numero_oficio",
        "caso__descripcion_breve",
        "titulo",
        "descripcion",
        "responsable__username",
    )
    list_filter = ("estado", ("fecha_compromiso", admin.DateFieldListFilter))
    autocomplete_fields = ("caso", "responsable", "creada_por", "completada_por")
    readonly_fields = ("creado_en", "actualizado_en", "completada_en")


@admin.register(models.LicenciaRegistro)
class LicenciaRegistroAdmin(admin.ModelAdmin):
    date_hierarchy = "fecha_tramite"
    list_display = (
        "trabajador",
        "tipo_tramite",
        "tipo_prorroga",
        "estatus",
        "fecha_tramite",
        "creado_por",
    )
    list_filter = (
        "tipo_tramite",
        "tipo_prorroga",
        "sindicato",
        "estatus",
        ("fecha_tramite", admin.DateFieldListFilter),
    )
    search_fields = (
        "trabajador__nombre",
        "trabajador__rfc",
        "trabajador__curp",
        "numero_expediente",
    )
    autocomplete_fields = ("trabajador", "estatus")
    readonly_fields = ("fecha_registro", "actualizado_en")


@admin.register(models.HistorialEstatusLicencia)
class HistorialEstatusLicenciaAdmin(admin.ModelAdmin):
    date_hierarchy = "fecha_cambio"
    list_display = ("licencia", "estatus_anterior", "estatus_nuevo", "fecha_cambio", "usuario")
    list_filter = ("estatus_nuevo", ("fecha_cambio", admin.DateFieldListFilter))
    search_fields = ("licencia__trabajador__nombre", "usuario__username")
    autocomplete_fields = ("licencia", "estatus_anterior", "estatus_nuevo", "usuario")
    readonly_fields = ("fecha_cambio",)


@admin.register(models.MinutaCaso)
class MinutaCasoAdmin(admin.ModelAdmin):
    list_display = ("caso", "archivo", "creado_en")
    search_fields = ("caso__descripcion_breve", "caso__cct__cct", "archivo")
    autocomplete_fields = ("caso",)
    readonly_fields = ("creado_en",)


@admin.register(models.MinutaTramite)
class MinutaTramiteAdmin(admin.ModelAdmin):
    list_display = ("tramite", "archivo", "creado_en")
    search_fields = ("tramite__caso__descripcion_breve", "tramite__caso__cct__cct", "archivo")
    autocomplete_fields = ("tramite",)
    readonly_fields = ("creado_en",)


@admin.register(models.FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("codigo", "modulo", "habilitado", "habilitado_por_defecto", "actualizado_en")
    list_filter = ("modulo", "habilitado", "habilitado_por_defecto")
    search_fields = ("codigo", "modulo", "nombre", "descripcion")
    ordering = ("modulo", "codigo")


@admin.register(models.FeatureFlagGrupo)
class FeatureFlagGrupoAdmin(admin.ModelAdmin):
    list_display = ("flag", "grupo", "habilitado", "actualizado_por", "actualizado_en")
    list_filter = ("habilitado", "grupo")
    search_fields = ("flag__codigo", "flag__modulo", "grupo__name")
    autocomplete_fields = ("flag", "grupo", "actualizado_por")


@admin.register(models.ScheduledJob)
class ScheduledJobAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "handler",
        "intervalo_minutos",
        "activo",
        "proxima_ejecucion",
        "ultimo_estado",
    )
    list_filter = ("activo", "ultimo_estado")
    search_fields = ("codigo", "nombre", "handler")


@admin.register(models.AsyncJob)
class AsyncJobAdmin(admin.ModelAdmin):
    list_display = (
        "job_type",
        "estado",
        "prioridad",
        "intentos",
        "max_intentos",
        "ejecutar_despues_de",
        "creado_en",
    )
    list_filter = ("estado", "job_type", "prioridad")
    search_fields = ("job_type", "error_mensaje", "scheduled_job__codigo")
    autocomplete_fields = ("creado_por", "scheduled_job")
    readonly_fields = ("creado_en", "iniciado_en", "finalizado_en")


@admin.register(models.DataQualityRun)
class DataQualityRunAdmin(admin.ModelAdmin):
    list_display = ("id", "origen", "estado", "iniciado_en", "finalizado_en", "ejecutado_por")
    list_filter = ("origen", "estado")
    search_fields = ("id", "error")
    autocomplete_fields = ("ejecutado_por", "async_job")
    readonly_fields = ("iniciado_en", "finalizado_en")


@admin.register(models.DataQualityIssue)
class DataQualityIssueAdmin(admin.ModelAdmin):
    list_display = (
        "categoria",
        "severidad",
        "entidad_tipo",
        "entidad_id",
        "regla_codigo",
        "activo",
        "ultimo_detectado_en",
    )
    list_filter = ("categoria", "severidad", "entidad_tipo", "activo")
    search_fields = ("regla_codigo", "titulo", "descripcion")
    autocomplete_fields = ("caso", "tramite", "licencia", "ultima_corrida")


@admin.register(models.EventoSistema)
class EventoSistemaAdmin(admin.ModelAdmin):
    list_display = ("categoria", "accion", "descripcion", "actor", "creado_en")
    list_filter = ("categoria", "accion", ("creado_en", admin.DateFieldListFilter))
    search_fields = ("descripcion", "detalle", "request_id")
    autocomplete_fields = ("actor", "caso", "tramite", "licencia")
    readonly_fields = ("creado_en",)


@admin.register(models.BitacoraCambioCritico)
class BitacoraCambioCriticoAdmin(admin.ModelAdmin):
    list_display = ("modulo", "accion", "descripcion", "actor", "creado_en")
    list_filter = ("modulo", "accion", ("creado_en", admin.DateFieldListFilter))
    search_fields = ("descripcion", "objeto_repr", "request_id")
    autocomplete_fields = ("actor", "caso", "tramite", "licencia")
    readonly_fields = ("creado_en",)


@admin.register(models.FiltroGuardadoUsuario)
class FiltroGuardadoUsuarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "alcance", "usuario", "actualizado_en")
    list_filter = ("alcance", ("actualizado_en", admin.DateFieldListFilter))
    search_fields = ("nombre", "usuario__username", "query_string")
    autocomplete_fields = ("usuario",)
    readonly_fields = ("creado_en", "actualizado_en")


class PermissionLabelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj: Permission) -> str:
        codename = obj.codename or ""
        action_map = {
            "add": _("Puede agregar"),
            "change": _("Puede modificar"),
            "delete": _("Puede eliminar"),
            "view": _("Puede ver"),
        }
        action = next(
            (key for key in action_map if codename.startswith(f"{key}_")),
            None,
        )
        if action:
            model_class = obj.content_type.model_class()
            model_name = (
                model_class._meta.verbose_name
                if model_class is not None
                else obj.content_type.name
            )
            return f"{action_map[action]} {model_name}"
        return obj.name


class PermissionSpanishMixin:
    permission_queryset = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label",
        "content_type__model",
        "codename",
    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name in {"permissions", "user_permissions"}:
            kwargs.setdefault("queryset", self.permission_queryset)
            kwargs.setdefault("form_class", PermissionLabelMultipleChoiceField)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class CustomGroupAdmin(PermissionSpanishMixin, GroupAdmin):
    pass


class CustomUserAdmin(PermissionSpanishMixin, UserAdmin):
    pass


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(get_user_model())
except admin.sites.NotRegistered:
    pass

admin.site.register(Group, CustomGroupAdmin)
admin.site.register(get_user_model(), CustomUserAdmin)
