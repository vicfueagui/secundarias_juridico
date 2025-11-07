"""Consultas para KPIs operativos."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.utils import timezone

from licencias import models


def _format_serie(queryset, campo_nombre: str, campo_valor: str) -> List[Dict[str, str]]:
    return [
        {"label": registro[campo_nombre], "value": registro[campo_valor]}
        for registro in queryset
    ]


def obtener_kpis_resumen() -> Dict[str, object]:
    hoy = timezone.now()
    hace_12_meses = hoy - timedelta(days=365)

    tramites = models.Tramite.objects.all()

    total_tramites = tramites.count()
    abiertos = tramites.exclude(
        estado_actual__nombre__icontains="cierre"
    ).count()
    cerrados = total_tramites - abiertos

    por_mes = (
        tramites.filter(created_at__gte=hace_12_meses)
        .annotate(mes=F("created_at__month"), anno=F("created_at__year"))
        .values("anno", "mes")
        .annotate(conteo=Count("id"))
        .order_by("anno", "mes")
    )

    por_tipo = (
        tramites.values("tipo_tramite__nombre")
        .annotate(conteo=Count("id"))
        .order_by("-conteo")
    )

    por_subsistema = (
        tramites.values("subsistema__nombre")
        .annotate(conteo=Count("id"))
        .order_by("-conteo")
    )

    por_etapa = (
        tramites.values("estado_actual__nombre")
        .annotate(conteo=Count("id"))
        .order_by("-conteo")
    )

    top_sindicatos = (
        tramites.values("sindicato__nombre")
        .annotate(conteo=Count("id"))
        .order_by("-conteo")[:5]
    )

    # Edad promedio de trámites abiertos
    edad_promedio = None
    if abiertos:
        edad_promedio = (
            tramites.exclude(
                estado_actual__nombre__icontains="cierre"
            ).aggregate(
                promedio=Avg(
                    ExpressionWrapper(
                        hoy - F("created_at"), output_field=DurationField()
                    )
                )
            )["promedio"]
        )

    return {
        "total_tramites": total_tramites,
        "abiertos": abiertos,
        "cerrados": cerrados,
        "serie_por_mes": list(por_mes),
        "serie_por_tipo": _format_serie(por_tipo, "tipo_tramite__nombre", "conteo"),
        "serie_por_subsistema": _format_serie(
            por_subsistema, "subsistema__nombre", "conteo"
        ),
        "serie_por_etapa": _format_serie(por_etapa, "estado_actual__nombre", "conteo"),
        "top_sindicatos": _format_serie(top_sindicatos, "sindicato__nombre", "conteo"),
        "edad_promedio": edad_promedio.total_seconds() / 86400 if edad_promedio else 0,
    }
