"""Validaciones de negocio para el dominio de licencias."""
from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from django.core.exceptions import ValidationError
from django.utils.text import slugify


def validar_fecha_pasado(valor: Optional[date], nombre_campo: str) -> None:
    """Verifica que la fecha no esté en el futuro."""
    if valor and valor > date.today():
        raise ValidationError({nombre_campo: "La fecha no puede ser futura."})


def validar_fechas_chronologicas(tramite) -> None:
    """Valida consistencia cronológica entre las fechas principales."""
    secuencia = [
        ("fecha_recepcion_nivel", tramite.fecha_recepcion_nivel),
        ("fecha_recepcion_subsecretaria", tramite.fecha_recepcion_subsecretaria),
        ("fecha_recepcion_rh", tramite.fecha_recepcion_rh),
    ]
    ultima_fecha = None
    ultimo_nombre = ""
    for nombre, valor in secuencia:
        validar_fecha_pasado(valor, nombre)
        if valor:
            if ultima_fecha and valor < ultima_fecha:
                raise ValidationError(
                    {
                        nombre: (
                            f"La fecha no puede ser anterior a {ultimo_nombre.replace('_', ' ')}."
                        )
                    }
                )
            ultima_fecha = valor
            ultimo_nombre = nombre


def validar_campos_por_etapa(tramite) -> None:
    """Reglas de obligatoriedad según la etapa."""
    if not getattr(tramite, "estado_actual_id", None):
        return

    etapa_slug = normalizar_etapa(tramite.estado_actual.nombre)
    if etapa_slug in {"resolucion", "notificacion", "cierre"}:
        if not tramite.oficio_resolucion_num_y_fecha:
            raise ValidationError(
                {"oficio_resolucion_num_y_fecha": "Captura el oficio de resolución."}
            )
        if not tramite.resultado_resolucion:
            raise ValidationError(
                {"resultado_resolucion": "Selecciona el resultado de la resolución."}
            )

    if etapa_slug in {"notificacion", "cierre"} and tramite.pk:
        if not tramite.notificaciones.exists():
            raise ValidationError(
                {
                    "estado_actual": (
                        "Para avanzar a notificación/cierre registra al menos una notificación."
                    )
                }
            )


_TRANSICIONES_ETAPAS = {
    "ingreso": {"integracion"},
    "integracion": {"vistobueno", "resolucion"},
    "vistobueno": {"resolucion"},
    "resolucion": {"notificacion", "cierre"},
    "notificacion": {"cierre"},
    "cierre": set(),
}


def normalizar_etapa(nombre: str) -> str:
    return slugify(nombre or "").replace("-", "")


def validar_transicion_etapa(
    etapa_anterior, etapa_nueva, *, excepciones: Optional[Iterable[str]] = None
) -> None:
    """Verifica que la transición de etapas sea válida."""
    if not etapa_nueva:
        raise ValidationError({"estado_actual": "Selecciona una etapa válida."})

    if not etapa_anterior:
        # Alta inicial: debe iniciar en ingreso/integración.
        return

    if etapa_anterior == etapa_nueva:
        return

    slug_anterior = normalizar_etapa(etapa_anterior.nombre)
    slug_nueva = normalizar_etapa(etapa_nueva.nombre)

    excepciones = set(excepciones or [])
    if slug_nueva in excepciones:
        return

    permitidas = _TRANSICIONES_ETAPAS.get(slug_anterior, set())
    if slug_nueva not in permitidas:
        raise ValidationError(
            {
                "estado_actual": (
                    f"No es válido pasar de {etapa_anterior.nombre} a {etapa_nueva.nombre}."
                )
            }
        )
