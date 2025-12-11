"""Filtros con django-filter para el módulo de trámites."""
from __future__ import annotations

import django_filters
from django.db.models import Q

from tramites import models


class CasoInternoFilter(django_filters.FilterSet):
    buscar = django_filters.CharFilter(
        method="filter_buscar",
        label="Buscar (CCT, folio, descripción)",
    )
    fecha_apertura = django_filters.DateFromToRangeFilter(label="Rango fecha apertura")

    class Meta:
        model = models.CasoInterno
        fields = {
            "cct": ["exact"],
            "estatus": ["exact"],
            "tipo_inicial": ["exact"],
            "area_origen_inicial": ["exact"],
        }

    def filter_buscar(self, queryset, _name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(descripcion_breve__icontains=value)
            | Q(folio_inicial__icontains=value)
            | Q(numero_oficio__icontains=value)
            | Q(cct_nombre__icontains=value)
            | Q(cct__cct__icontains=value)
        )
