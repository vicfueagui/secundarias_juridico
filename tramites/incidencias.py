"""Lógica compartida para la captura de incidencias en trámites."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

AFILIACION_IMSS = "IMSS"
AFILIACION_ISSSTE = "ISSSTE"
AFILIACION_CHOICES = (
    (AFILIACION_IMSS, "IMSS"),
    (AFILIACION_ISSSTE, "ISSSTE"),
)

INCIDENCIA_FIELD_NAMES = (
    "incidencia_nombre_docente",
    "incidencia_afiliacion",
    "incidencia_fecha_inicio",
    "incidencia_fecha_termino",
    "incidencia_dias_otorgados",
)


def normalise_incidencias(payload: Dict[str, Any], *, error_class=ValidationError) -> Dict[str, Any]:
    """Valida y normaliza los campos de incidencias.

    - Si no hay datos, devuelve todos los campos reseteados sin error.
    - Para ISSSTE: calcula días naturales a partir de inicio/término.
    - Para IMSS: calcula fecha de término a partir de inicio + días.
    """

    errors: dict[str, list[str]] = {}
    nombre = (payload.get("incidencia_nombre_docente") or "").strip()
    afiliacion = (payload.get("incidencia_afiliacion") or "").strip().upper()
    fecha_inicio = payload.get("incidencia_fecha_inicio")
    fecha_termino = payload.get("incidencia_fecha_termino")
    dias_otorgados_raw = payload.get("incidencia_dias_otorgados")
    dias_otorgados = None

    if dias_otorgados_raw not in (None, ""):
        try:
            dias_otorgados = int(dias_otorgados_raw)
        except (TypeError, ValueError):
            errors["incidencia_dias_otorgados"] = [_("Ingresa un número entero de días naturales.")]

    has_data = bool(
        afiliacion
        or fecha_inicio
        or fecha_termino
        or dias_otorgados_raw not in (None, "")
    )

    normalised = {
        "incidencia_nombre_docente": nombre,
        "incidencia_afiliacion": afiliacion,
        "incidencia_fecha_inicio": fecha_inicio,
        "incidencia_fecha_termino": fecha_termino,
        "incidencia_dias_otorgados": dias_otorgados,
    }

    if not has_data:
        normalised["incidencia_afiliacion"] = ""
        normalised["incidencia_fecha_inicio"] = None
        normalised["incidencia_fecha_termino"] = None
        normalised["incidencia_dias_otorgados"] = None
        if errors:
            raise error_class(errors)
        return normalised

    if afiliacion and afiliacion not in {AFILIACION_IMSS, AFILIACION_ISSSTE}:
        errors["incidencia_afiliacion"] = [_("Selecciona IMSS o ISSSTE.")]

    if not afiliacion:
        errors["incidencia_afiliacion"] = [_("Selecciona la afiliación para calcular la incidencia.")]

    if not fecha_inicio:
        errors["incidencia_fecha_inicio"] = [_("Captura la fecha de inicio de la incidencia.")]

    if afiliacion == AFILIACION_ISSSTE:
        if not fecha_termino:
            errors["incidencia_fecha_termino"] = [_("Captura la fecha de término.")]
        elif fecha_inicio and fecha_termino < fecha_inicio:
            errors["incidencia_fecha_termino"] = [_("La fecha de término no puede ser anterior a la de inicio.")]
        if fecha_inicio and fecha_termino:
            dias_calculados = (fecha_termino - fecha_inicio).days + 1
            if dias_calculados <= 0:
                errors["incidencia_dias_otorgados"] = [_("El periodo debe cubrir al menos un día.")]
            else:
                normalised["incidencia_dias_otorgados"] = dias_calculados
    elif afiliacion == AFILIACION_IMSS:
        if dias_otorgados is None:
            errors["incidencia_dias_otorgados"] = [_("Captura los días otorgados por la licencia.")]
        elif dias_otorgados <= 0:
            errors["incidencia_dias_otorgados"] = [_("Los días otorgados deben ser mayores a cero.")]
        if fecha_inicio and dias_otorgados and dias_otorgados > 0:
            normalised["incidencia_fecha_termino"] = fecha_inicio + timedelta(days=dias_otorgados - 1)
            normalised["incidencia_dias_otorgados"] = dias_otorgados

    if errors:
        raise error_class(errors)

    return normalised


def apply_incidencias(instance, *, error_class=ValidationError) -> None:
    """Aplica la validación y normalización directamente sobre una instancia."""
    payload = {field: getattr(instance, field, None) for field in INCIDENCIA_FIELD_NAMES}
    normalised = normalise_incidencias(payload, error_class=error_class)
    for field, value in normalised.items():
        setattr(instance, field, value)
