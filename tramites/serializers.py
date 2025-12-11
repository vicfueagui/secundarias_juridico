"""Serializadores para la API restante (CCT y Catálogos)."""
from __future__ import annotations

from typing import Any

from rest_framework import serializers

from tramites import models
from tramites.utils import normalise_sistema


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


class TipoProcesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TipoProceso
        fields = (
            "id",
            "nombre",
            "descripcion",
            "esta_activo",
            "es_documento",
        )

    def validate_nombre(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Este campo es obligatorio.")
        return value


class EstatusCasoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EstatusCaso
        fields = (
            "id",
            "nombre",
            "esta_activo",
            "orden",
        )

    def validate_nombre(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Este campo es obligatorio.")
        return value


class TipoViolenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TipoViolencia
        fields = (
            "id",
            "nombre",
            "descripcion",
            "esta_activo",
        )

    def validate_nombre(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Este campo es obligatorio.")
        return value


class PrefijoOficioSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PrefijoOficio
        fields = (
            "id",
            "nombre",
            "descripcion",
            "esta_activo",
        )

    def validate_nombre(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Este campo es obligatorio.")
        return value


class SolicitanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Solicitante
        fields = (
            "id",
            "nombre",
            "descripcion",
            "esta_activo",
        )

    def validate_nombre(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Este campo es obligatorio.")
        return value


class DestinatarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Destinatario
        fields = (
            "id",
            "nombre",
            "descripcion",
            "esta_activo",
        )

    def validate_nombre(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Este campo es obligatorio.")
        return value


class TramiteCasoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TramiteCaso
        fields = (
            "id",
            "caso",
            "tipo",
            "estatus",
            "tipo_violencia",
            "solicitante",
            "dirigido_a",
            "fecha",
            "numero_oficio",
            "asunto",
            "observaciones",
            "generador_nombre",
            "generador_iniciales",
            "generador_sexo",
            "receptor_nombre",
            "receptor_iniciales",
            "receptor_sexo",
            "receptores_adicionales",
            "creado_en",
            "actualizado_en",
        )

    def validate_asunto(self, value: str) -> str:
        return (value or "").strip()


class EstatusTramiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EstatusTramite
        fields = (
            "id",
            "nombre",
            "descripcion",
            "esta_activo",
            "orden",
        )

    def validate_nombre(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Este campo es obligatorio.")
        return value
