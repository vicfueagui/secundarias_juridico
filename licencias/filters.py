"""Filtros con django-filter para Tramite."""
from __future__ import annotations

import django_filters
from django.db.models import Q

from licencias import models


class TramiteFilter(django_filters.FilterSet):
    folio = django_filters.CharFilter(lookup_expr="icontains", label="Folio")
    trabajador = django_filters.CharFilter(
        field_name="trabajador_nombre", lookup_expr="icontains", label="Trabajador"
    )
    fecha_recepcion_nivel = django_filters.DateFromToRangeFilter(
        label="Rango recepción nivel"
    )
    fecha_recepcion_rh = django_filters.DateFromToRangeFilter(
        label="Rango recepción RH"
    )
    fecha_movimiento = django_filters.DateFromToRangeFilter(
        field_name="movimientos__fecha",
        label="Rango último movimiento",
    )

    class Meta:
        model = models.Tramite
        fields = {
            "tipo_tramite": ["exact"],
            "subsistema": ["exact"],
            "sindicato": ["exact"],
            "resultado_resolucion": ["exact"],
            "estado_actual": ["exact"],
            "user_responsable": ["exact"],
        }


class RelacionProtocoloFilter(django_filters.FilterSet):
    buscar = django_filters.CharFilter(
        method="filter_buscar", label="Buscar (folio, NNA, violencia)"
    )
    fecha_inicio = django_filters.DateFromToRangeFilter(label="Rango fecha inicio")

    class Meta:
        model = models.RelacionProtocolo
        fields = {
            "cct": ["exact"],
            "estatus": ["exact"],
            "anio": ["exact"],
            "sexo": ["exact"],
        }

    def filter_buscar(self, queryset, _name, value):
        if not value:
            return queryset
        query = (
            Q(nombre_nna__icontains=value)
            | Q(iniciales__icontains=value)
            | Q(tipo_violencia__icontains=value)
            | Q(comentarios__icontains=value)
        )
        try:
            numero = int(value)
        except (TypeError, ValueError):
            numero = None
        if numero is not None:
            query |= Q(numero_registro=numero)
        return queryset.filter(query)


class ControlInternoFilter(django_filters.FilterSet):
    buscar = django_filters.CharFilter(
        method="filter_buscar", label="Buscar (memorándum, asunto, número interno, CCT)"
    )
    fecha_memorandum = django_filters.DateFromToRangeFilter(
        label="Rango fecha memorándum"
    )
    fecha_contestacion = django_filters.DateFromToRangeFilter(
        label="Rango fecha contestación"
    )

    class Meta:
        model = models.ControlInterno
        fields = {
            "anio": ["exact"],
            "estatus": ["exact"],
            "asesor": ["exact"],
        }

    def filter_buscar(self, queryset, _name, value):
        if not value:
            return queryset
        query = (
            Q(memorandum__icontains=value)
            | Q(numero_interno__icontains=value)
            | Q(asunto__icontains=value)
            | Q(cct_nombre__icontains=value)
            | Q(cct__cct__icontains=value)
        )
        return queryset.filter(query)
