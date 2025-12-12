"""Filtros con django-filter para el módulo de trámites."""
from __future__ import annotations

import django_filters
from django.db.models import Q
from django.contrib.auth import get_user_model
from django import forms

from tramites import models


class CasoInternoFilter(django_filters.FilterSet):
    buscar = django_filters.CharFilter(
        method="filter_buscar",
        label="Buscar (CCT, folio, descripción)",
    )
    fecha_apertura = django_filters.DateFromToRangeFilter(
        label="Rango fecha apertura",
        widget=django_filters.widgets.RangeWidget(attrs={"type": "date"}),
    )
    creado_por = django_filters.ModelChoiceFilter(
        queryset=get_user_model().objects.all(),
        label="Usuario",
    )
    generador_iniciales = django_filters.CharFilter(
        field_name="generador_iniciales",
        lookup_expr="icontains",
        label="Iniciales generador",
    )
    receptor_iniciales = django_filters.CharFilter(
        field_name="receptor_iniciales",
        lookup_expr="icontains",
        label="Iniciales receptor",
    )
    asesor_cct = django_filters.CharFilter(
        field_name="asesor_cct",
        lookup_expr="icontains",
        label="Asesor CCT",
    )
    fecha_registro = django_filters.DateFromToRangeFilter(
        label="Rango fecha de registro",
        widget=django_filters.widgets.RangeWidget(attrs={"type": "date"}),
    )

    class Meta:
        model = models.CasoInterno
        fields = {
            "cct": ["exact"],
            "estatus": ["exact"],
            "tipo_inicial": ["exact"],
            "creado_por": ["exact"],
            "asesor_cct": ["icontains"],
            "fecha_registro": ["exact"],
        }

    def filter_buscar(self, queryset, _name, value):
        if not value:
            return queryset
        return (
            queryset.filter(
                Q(descripcion_breve__icontains=value)
                | Q(asunto__icontains=value)
                | Q(folio_inicial__icontains=value)
                | Q(numero_oficio__icontains=value)
                | Q(cct_nombre__icontains=value)
                | Q(cct__cct__icontains=value)
                | Q(tipo_inicial__nombre__icontains=value)
                | Q(estatus__nombre__icontains=value)
                | Q(tipo_violencia__nombre__icontains=value)
                | Q(solicitante__nombre__icontains=value)
                | Q(dirigido_a__nombre__icontains=value)
                | Q(generador_nombre__icontains=value)
                | Q(generador_iniciales__icontains=value)
                | Q(receptor_nombre__icontains=value)
                | Q(receptor_iniciales__icontains=value)
                | Q(asesor_cct__icontains=value)
                | Q(creado_por__username__icontains=value)
            )
            .distinct()
        )
