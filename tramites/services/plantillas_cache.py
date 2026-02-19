from __future__ import annotations

from typing import Any

from django.core.cache import cache

from tramites import models
from tramites.utils import normalise_sistema

CACHE_TTL_SECONDS = 300


def _build_cache_key(empleado_id: int) -> str:
    return f"plantilla_latest_{empleado_id}"


def clear_empleado_cache(empleado_id: int) -> None:
    cache.delete(_build_cache_key(empleado_id))


def get_latest_registro_info(empleado_id: int) -> dict[str, Any]:
    cache_key = _build_cache_key(empleado_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs = (
        models.PlantillaRegistro.objects.filter(empleado_id=empleado_id)
        .select_related("centro_trabajo")
        .prefetch_related("claves")
        .order_by("-anio", "-ciclo", "centro_trabajo__cct")
    )
    latest = qs.first()
    if not latest:
        data = {
            "ultimo_anio": None,
            "ultimo_ciclo": "",
            "centros": [],
            "registros": [],
        }
        cache.set(cache_key, data, CACHE_TTL_SECONDS)
        return data

    ultimo_anio = latest.anio
    ultimo_ciclo = latest.ciclo
    registros = list(qs.filter(anio=ultimo_anio, ciclo=ultimo_ciclo))

    centros = []
    seen = set()
    for registro in registros:
        centro = registro.centro_trabajo
        if not centro:
            continue
        if centro.cct in seen:
            continue
        seen.add(centro.cct)
        centros.append(
            {
                "cct": centro.cct,
                "nombre": centro.nombre,
                "asesor": centro.asesor or "",
                "sistema": normalise_sistema(centro.sostenimiento),
                "modalidad": centro.subnivel or "",
                "municipio": centro.municipio or "",
                "turno": centro.turno or "",
            }
        )

    registros_payload = []
    for registro in registros:
        centro = registro.centro_trabajo
        registros_payload.append(
            {
                "registro_id": registro.id,
                "cct": centro.cct if centro else "",
                "nombre": centro.nombre if centro else "",
                "situacion": registro.situacion or "",
                "funcion": registro.funcion or "",
                "grado_grupo_horas": registro.grado_grupo_horas or "",
                "anio": registro.anio,
                "ciclo": registro.ciclo or "",
                "claves": [clave.clave for clave in registro.claves.all()],
            }
        )

    data = {
        "ultimo_anio": ultimo_anio,
        "ultimo_ciclo": ultimo_ciclo or "",
        "centros": centros,
        "registros": registros_payload,
    }
    cache.set(cache_key, data, CACHE_TTL_SECONDS)
    return data
