"""Modelos del módulo de incidencias y reporteador."""
from __future__ import annotations

from django.db import models
from django.template import Context, Template
from django.utils import timezone
from django.utils.formats import date_format


class Incidencia(models.Model):
    """Registro base de una incidencia capturada desde el formulario."""

    numero = models.CharField("No.", max_length=20, unique=True)
    apellido_paterno = models.CharField(max_length=50)
    apellido_materno = models.CharField(max_length=50, blank=True)
    nombres = models.CharField(max_length=100)
    rfc = models.CharField("R.F.C", max_length=13)
    filiacion = models.CharField(max_length=50, blank=True)
    cct = models.CharField("C.C.T", max_length=20)
    numero_serie = models.CharField("No. serie", max_length=50, blank=True)
    dias = models.PositiveIntegerField("Días")
    fecha_del = models.DateField("Del")
    fecha_al = models.DateField("Al")
    cuerpo_personalizado = models.TextField(
        "Cuerpo del reporte (editable)",
        blank=True,
        help_text="Si se deja vacío, se usará la plantilla por defecto configurada en admin.",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-creado_en",)
        verbose_name = "Incidencia"
        verbose_name_plural = "Incidencias"

    def __str__(self) -> str:  # pragma: no cover - representación simple
        return f"Incidencia {self.numero} - {self.nombre_completo}"

    @property
    def nombre_completo(self) -> str:
        partes = [self.apellido_paterno.strip()]
        if self.apellido_materno:
            partes.append(self.apellido_materno.strip())
        partes.append(self.nombres.strip())
        return " ".join(filter(None, partes))

    def get_contexto_reporte(self) -> dict[str, str]:
        """Prepara las variables disponibles para las plantillas."""
        fecha_del_fmt = date_format(self.fecha_del, "DATE_FORMAT")
        fecha_al_fmt = date_format(self.fecha_al, "DATE_FORMAT")
        hoy_fmt = date_format(timezone.localdate(), "DATE_FORMAT")
        return {
            "numero": self.numero,
            "nombre_completo": self.nombre_completo,
            "apellido_paterno": self.apellido_paterno,
            "apellido_materno": self.apellido_materno,
            "nombres": self.nombres,
            "rfc": self.rfc,
            "filiacion": self.filiacion,
            "cct": self.cct,
            "numero_serie": self.numero_serie,
            "dias": self.dias,
            "fecha_del": self.fecha_del,
            "fecha_al": self.fecha_al,
            "fecha_del_formateada": fecha_del_fmt,
            "fecha_al_formateada": fecha_al_fmt,
            "fecha_rango": f"del {fecha_del_fmt} al {fecha_al_fmt}",
            "fecha_actual": hoy_fmt,
        }


class PlantillaReporteIncidencia(models.Model):
    """Configuración membretada del reporte de incidencias."""

    nombre = models.CharField(max_length=100, default="Incidencias")
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    titulo = models.CharField(
        max_length=200,
        default="RELACIÓN DE LICENCIAS MÉDICAS CORRESPONDIENTES AL PERSONAL DE BASE A DISPOSICIÓN (PROTOCOLO)",
    )
    cuerpo_base = models.TextField(
        help_text="Texto base del reporte. Puedes usar variables como {{ nombre_completo }}.",
        default=(
            "Por medio de la presente se informa que {{ nombre_completo }} "
            "con RFC {{ rfc }} cuenta con {{ dias }} días de licencia médica "
            "{{ fecha_rango }}."
        ),
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plantilla de reporte de incidencia"
        verbose_name_plural = "Plantillas de reporte de incidencias"

    def __str__(self) -> str:  # pragma: no cover - representación simple
        return self.nombre

    def render_cuerpo(self, incidencia: Incidencia) -> str:
        """Genera el cuerpo a partir del template base y los datos de la incidencia."""
        contexto = incidencia.get_contexto_reporte()
        template = Template(self.cuerpo_base)
        return template.render(Context(contexto))
