"""Serializadores para la API restante (CCT y Catálogos)."""
from __future__ import annotations

from typing import Any

from rest_framework import serializers

from tramites import models
from tramites.incidencias import normalise_incidencias
from tramites.utils import normalise_sistema


class PlantillaCentroTrabajoSerializer(serializers.ModelSerializer):
    servicio = serializers.CharField(source="subnivel", allow_blank=True, required=False)

    class Meta:
        model = models.PlantillaCentroTrabajo
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

    def to_representation(self, instance: models.PlantillaCentroTrabajo) -> dict[str, Any]:
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


class FolioPrefijoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FolioPrefijo
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
            "cct",
            "cct_nombre",
            "cct_sistema",
            "cct_modalidad",
            "asesor_cct",
            "tipo",
            "estatus",
            "tipo_violencia",
            "tipos_violencia_adicionales",
            "solicitante",
            "dirigido_a",
            "fecha",
            "numero_oficio",
            "tipo_prorroga",
            "sindicato",
            "diagnostico",
            "asunto",
            "observaciones",
            "minuta",
            "generador_nombre",
            "generador_iniciales",
            "generador_sexo",
            "receptor_nombre",
            "receptor_iniciales",
            "receptor_sexo",
            "receptores_adicionales",
            "creado_en",
            "actualizado_en",
            "incidencia_nombre_docente",
            "incidencia_afiliacion",
            "incidencia_fecha_inicio",
            "incidencia_fecha_termino",
            "incidencia_dias_otorgados",
            "rangos_fechas_adicionales",
        )

    def validate_asunto(self, value: str) -> str:
        return (value or "").strip()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        normalised = normalise_incidencias(attrs, error_class=serializers.ValidationError)
        attrs.update(normalised)
        return attrs


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


class SLAReglaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SLARegla
        fields = (
            "id",
            "nombre",
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
            "orden",
        )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        ambito = attrs.get("ambito") or getattr(self.instance, "ambito", "")
        estatus_caso = attrs.get("estatus_caso") if "estatus_caso" in attrs else getattr(self.instance, "estatus_caso", None)
        estatus_tramite = (
            attrs.get("estatus_tramite")
            if "estatus_tramite" in attrs
            else getattr(self.instance, "estatus_tramite", None)
        )
        if ambito == models.SLARegla.AMBITO_CASO:
            if estatus_tramite:
                raise serializers.ValidationError({"estatus_tramite": "No aplica para reglas de caso."})
        elif ambito == models.SLARegla.AMBITO_TRAMITE:
            if estatus_caso:
                raise serializers.ValidationError({"estatus_caso": "No aplica para reglas de trámite."})
        else:
            raise serializers.ValidationError({"ambito": "Ámbito inválido para regla SLA."})
        peso = attrs.get("peso_riesgo")
        if peso is not None and (peso < 1 or peso > 100):
            raise serializers.ValidationError({"peso_riesgo": "Debe estar entre 1 y 100."})
        return attrs
