"""Filtros con django-filter para el módulo de trámites."""
from __future__ import annotations

import django_filters
from django_filters import fields as filter_fields
from django.db.models import Q
from django.contrib.auth import get_user_model
from django import forms

from tramites import models

DATE_INPUT_FORMATS = ["%Y-%m-%d", "%d/%m/%Y"]


class LocalizedDateRangeField(filter_fields.DateRangeField):
    def __init__(self, *args, **kwargs):
        fields = (
            forms.DateField(input_formats=DATE_INPUT_FORMATS),
            forms.DateField(input_formats=DATE_INPUT_FORMATS),
        )
        filter_fields.RangeField.__init__(self, fields, *args, **kwargs)


class LocalizedDateFromToRangeFilter(django_filters.DateFromToRangeFilter):
    field_class = LocalizedDateRangeField


class CasoInternoFilter(django_filters.FilterSet):
    buscar = django_filters.CharFilter(
        method="filter_buscar",
        label="Buscar (CCT, folio, descripción)",
    )
    fecha_apertura = LocalizedDateFromToRangeFilter(
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
    asesor_cct = django_filters.ChoiceFilter(
        field_name="asesor_cct",
        lookup_expr="exact",
        label="Asesor",
        empty_label="Todos",
    )
    tipo_violencia = django_filters.ChoiceFilter(
        method="filter_tipo_violencia",
        label="Tipo de violencia",
    )
    trabajador = django_filters.CharFilter(
        method="filter_trabajador",
        label="Trabajador (nombre, RFC o CURP)",
    )
    fecha_registro = LocalizedDateFromToRangeFilter(
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
            "asesor_cct": ["exact"],
            "tipo_violencia": ["exact"],
            "fecha_registro": ["exact"],
        }

    def filter_buscar(self, queryset, _name, value):
        if not value:
            return queryset
        query = (
            Q(descripcion_breve__icontains=value)
            | Q(asunto__icontains=value)
            | Q(folio_inicial__icontains=value)
            | Q(folios_generados__folio__icontains=value)
            | Q(numero_oficio__icontains=value)
            | Q(cct_nombre__icontains=value)
            | Q(cct__cct__icontains=value)
            | Q(centros_trabajo_adicionales__cct__icontains=value)
            | Q(centros_trabajo_adicionales__nombre__icontains=value)
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
            | Q(tramites_relacionados__numero_oficio__icontains=value)
            | Q(tramites_relacionados__folios_generados__folio__icontains=value)
            | Q(tramites_relacionados__asunto__icontains=value)
            | Q(tramites_relacionados__tipo__nombre__icontains=value)
            | Q(tramites_relacionados__estatus__nombre__icontains=value)
            | Q(trabajadores__nombre__icontains=value)
            | Q(trabajadores__rfc__icontains=value)
            | Q(trabajadores__curp__icontains=value)
        )
        if value.isdigit():
            caso_id = int(value)
            query |= Q(pk=caso_id) | Q(tramites_relacionados__pk=caso_id)
        return queryset.filter(query).distinct()

    def filter_trabajador(self, queryset, _name, value):
        if not value:
            return queryset
        return (
            queryset.filter(
                Q(trabajadores__nombre__icontains=value)
                | Q(trabajadores__rfc__icontains=value)
                | Q(trabajadores__curp__icontains=value)
            )
            .distinct()
        )

    def filter_tipo_violencia(self, queryset, _name, value):
        if not value:
            return queryset
        if value == "__all__":
            return queryset.exclude(tipo_violencia__isnull=True)
        return queryset.filter(tipo_violencia_id=value)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Llenar dinámicamente la lista de asesores disponibles.
        asesores = (
            models.CasoInterno.objects.exclude(asesor_cct="")
            .order_by("asesor_cct")
            .values_list("asesor_cct", flat=True)
            .distinct()
        )
        self.filters["asesor_cct"].extra["choices"] = [(a, a) for a in asesores]
        tipos_violencia = models.TipoViolencia.objects.order_by("nombre").values_list("id", "nombre")
        self.filters["tipo_violencia"].extra["choices"] = [
            ("", "Sin filtro"),
            ("__all__", "Todos"),
            *tipos_violencia,
        ]


class LicenciaRegistroFilter(django_filters.FilterSet):
    buscar = django_filters.CharFilter(
        method="filter_buscar",
        label="Buscar (trabajador, expediente)",
    )
    fecha_tramite = LocalizedDateFromToRangeFilter(
        label="Rango fecha trámite",
        widget=django_filters.widgets.RangeWidget(attrs={"type": "date"}),
    )

    class Meta:
        model = models.LicenciaRegistro
        fields = {
            "tipo_tramite": ["exact"],
            "tipo_prorroga": ["exact"],
            "sindicato": ["exact"],
            "estatus": ["exact"],
            "fecha_tramite": ["exact"],
        }

    def filter_buscar(self, queryset, _name, value):
        if not value:
            return queryset
        return (
            queryset.filter(
                Q(trabajador__nombre__icontains=value)
                | Q(trabajador__rfc__icontains=value)
                | Q(trabajador__curp__icontains=value)
                | Q(numero_expediente__icontains=value)
            )
            .distinct()
        )


class PlantillaEmpleadoFilter(django_filters.FilterSet):
    buscar = django_filters.CharFilter(
        method="filter_buscar",
        label="Buscar (nombre, RFC o CURP)",
    )

    class Meta:
        model = models.PlantillaEmpleado
        fields = ()

    def filter_buscar(self, queryset, _name, value):
        if not value:
            return queryset
        return (
            queryset.filter(
                Q(nombre__icontains=value)
                | Q(rfc__icontains=value)
                | Q(curp__icontains=value)
            )
            .distinct()
        )
