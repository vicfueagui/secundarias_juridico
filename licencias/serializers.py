"""Serializadores para la API de licencias."""
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from licencias import models
from licencias.utils import normalise_sistema
from licencias.services import validators

User = get_user_model()


class SubsistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Subsistema
        fields = ("id", "nombre", "descripcion", "esta_activo")


class TipoTramiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TipoTramite
        fields = ("id", "nombre", "descripcion", "esta_activo")


class EtapaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Etapa
        fields = ("id", "nombre", "descripcion", "orden", "es_final", "esta_activo")


class ResultadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Resultado
        fields = ("id", "nombre", "descripcion", "esta_activo")


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Area
        fields = ("id", "nombre", "descripcion", "esta_activo")


class SindicatoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Sindicato
        fields = ("id", "nombre", "descripcion", "esta_activo")


class DiagnosticoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Diagnostico
        fields = ("id", "nombre", "descripcion", "esta_activo")


class CCTSecundariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CCTSecundaria
        fields = (
            "cct",
            "nombre",
            "asesor",
            "servicio",
            "sostenimiento",
            "municipio",
            "turno",
        )

    def validate_cct(self, value: str) -> str:
        return (value or "").strip().upper()

    def validate_nombre(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Este campo es obligatorio.")
        return value

    def validate_sostenimiento(self, value: str) -> str:
        return normalise_sistema(value)

    def to_representation(self, instance: models.CCTSecundaria) -> dict[str, Any]:
        data = super().to_representation(instance)
        data["sostenimiento"] = normalise_sistema(data.get("sostenimiento"))
        return data


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email")


class OficioSerializer(serializers.ModelSerializer):
    area_emisora = serializers.StringRelatedField()

    class Meta:
        model = models.Oficio
        fields = (
            "id",
            "tipo",
            "numero",
            "fecha",
            "area_emisora",
            "observaciones",
        )


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Notificacion
        fields = (
            "id",
            "destinatario",
            "numero_oficio",
            "fecha",
            "observaciones",
        )


class MovimientoSerializer(serializers.ModelSerializer):
    etapa_anterior = serializers.StringRelatedField()
    etapa_nueva = serializers.StringRelatedField()
    usuario = UsuarioSerializer()

    class Meta:
        model = models.Movimiento
        fields = ("id", "etapa_anterior", "etapa_nueva", "comentario", "usuario", "fecha")


class TramiteSerializer(serializers.ModelSerializer):
    tipo_tramite = TipoTramiteSerializer(read_only=True)
    subsistema = SubsistemaSerializer(read_only=True)
    diagnostico = DiagnosticoSerializer(read_only=True)
    sindicato = SindicatoSerializer(read_only=True)
    resultado_resolucion = ResultadoSerializer(read_only=True)
    estado_actual = EtapaSerializer(read_only=True)
    user_responsable = UsuarioSerializer(read_only=True)
    oficios = OficioSerializer(many=True, read_only=True)
    notificaciones = NotificacionSerializer(many=True, read_only=True)
    movimientos = MovimientoSerializer(many=True, read_only=True)

    class Meta:
        model = models.Tramite
        fields = "__all__"
        read_only_fields = ("folio", "created_at", "updated_at", "history")


class TramiteWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Tramite
        fields = (
            "id",
            "folio",
            "tipo_tramite",
            "subsistema",
            "tramite_inicial_o_prorroga",
            "trabajador_nombre",
            "diagnostico",
            "sindicato",
            "contacto",
            "oficio_origen_num",
            "fecha_recepcion_nivel",
            "incidencias_integracion",
            "oficio_envio_subsecretaria",
            "fecha_recepcion_subsecretaria",
            "incidencias_vobo",
            "vobo_num_y_fecha",
            "oficio_envio_rh",
            "fecha_recepcion_rh",
            "oficio_resolucion_num_y_fecha",
            "resultado_resolucion",
            "persona_tramita",
            "estado_actual",
            "user_responsable",
            "observaciones",
        )
        read_only_fields = ("folio",)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        instance = self.instance or models.Tramite(**attrs)
        for key, value in attrs.items():
            setattr(instance, key, value)
        validators.validar_fechas_chronologicas(instance)
        validators.validar_campos_por_etapa(instance)
        etapa_anterior = None
        if instance.pk:
            original = instance.__class__.objects.filter(pk=instance.pk).first()
            if original:
                etapa_anterior = original.estado_actual
        nueva_etapa = attrs.get("estado_actual", instance.estado_actual)
        validators.validar_transicion_etapa(etapa_anterior, nueva_etapa)
        return attrs


class TramiteListSerializer(serializers.ModelSerializer):
    tipo_tramite = serializers.StringRelatedField()
    subsistema = serializers.StringRelatedField()
    sindicato = serializers.StringRelatedField()
    estado_actual = serializers.StringRelatedField()
    user_responsable = serializers.StringRelatedField()

    class Meta:
        model = models.Tramite
        fields = (
            "id",
            "folio",
            "trabajador_nombre",
            "tipo_tramite",
            "subsistema",
            "sindicato",
            "estado_actual",
            "fecha_recepcion_nivel",
            "resultado_resolucion",
            "user_responsable",
            "updated_at",
        )
