"""Formularios para capturar incidencias y editar reportes."""
from __future__ import annotations

from django import forms

from incidencias import models


class IncidenciaForm(forms.ModelForm):
    class Meta:
        model = models.Incidencia
        fields = [
            "numero",
            "apellido_paterno",
            "apellido_materno",
            "nombres",
            "rfc",
            "filiacion",
            "cct",
            "numero_serie",
            "dias",
            "fecha_del",
            "fecha_al",
        ]
        widgets = {
            "fecha_del": forms.DateInput(attrs={"type": "date"}),
            "fecha_al": forms.DateInput(attrs={"type": "date"}),
        }


class IncidenciaReporteForm(forms.ModelForm):
    class Meta:
        model = models.Incidencia
        fields = ["cuerpo_personalizado"]
        widgets = {
            "cuerpo_personalizado": forms.Textarea(attrs={"rows": 12}),
        }
