from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from tramites import models
from tramites.services import sla

CRITICAL_WINDOW_DAYS = 2
STALE_WINDOW_DAYS = 4


def _is_critical_by_status(status_name: str) -> bool:
    normalized = (status_name or "").strip().lower()
    return any(keyword in normalized for keyword in ("urgente", "critico", "crítico", "riesgo"))


def _priority_score(*, dias_para_termino: int | None, dias_sin_movimiento: int, status_name: str) -> int:
    score = 15
    if dias_para_termino is not None:
        if dias_para_termino < 0:
            score += 140 + min(abs(dias_para_termino), 30)
        elif dias_para_termino <= CRITICAL_WINDOW_DAYS:
            score += 100 - (dias_para_termino * 15)
        elif dias_para_termino <= 7:
            score += 50 - (dias_para_termino * 5)
    if dias_sin_movimiento >= STALE_WINDOW_DAYS:
        score += 35 + min(dias_sin_movimiento - STALE_WINDOW_DAYS, 20)
    if _is_critical_by_status(status_name):
        score += 35
    elif "pendiente" in (status_name or "").strip().lower():
        score += 12
    return max(score, 1)


def _priority_label(score: int) -> str:
    if score >= 170:
        return "Crítica"
    if score >= 110:
        return "Alta"
    if score >= 60:
        return "Media"
    return "Normal"


def _priority_class(label: str) -> str:
    if label == "Crítica":
        return "critica"
    if label == "Alta":
        return "alta"
    if label == "Media":
        return "media"
    return "normal"


def _to_case_item(
    caso: models.CasoInterno,
    *,
    today,
    now,
    sla_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fecha_limite = None
    dias_para_termino = None
    if sla_snapshot:
        fecha_limite = sla_snapshot.get("fecha_vencimiento")
        dias_para_termino = sla_snapshot.get("dias_restantes")
    if fecha_limite is None:
        fecha_limite = caso.fecha_termino or caso.incidencia_fecha_termino
    if dias_para_termino is None and fecha_limite:
        dias_para_termino = (fecha_limite - today).days
    dias_sin_movimiento = max((now - caso.actualizado_en).days, 0)
    estatus_name = getattr(caso.estatus, "nombre", "") or "Sin estatus"
    score = int((sla_snapshot or {}).get("riesgo_score") or 0)
    if not score:
        score = _priority_score(
            dias_para_termino=dias_para_termino,
            dias_sin_movimiento=dias_sin_movimiento,
            status_name=estatus_name,
        )
    if dias_sin_movimiento >= STALE_WINDOW_DAYS:
        score += 8
    priority_label = _priority_label(score)
    semaforo = (sla_snapshot or {}).get("semaforo")
    is_critical_sla = semaforo in {"amarillo", "rojo"}
    is_overdue_sla = semaforo == "rojo"
    return {
        "tipo": "caso",
        "id": caso.pk,
        "referencia": f"Caso #{caso.pk}",
        "caso_id": caso.pk,
        "tramite_id": None,
        "expediente": (caso.numero_oficio or "").strip() or "Sin expediente",
        "asunto": (caso.asunto or caso.descripcion_breve or "").strip(),
        "estatus": estatus_name,
        "fecha_limite": fecha_limite,
        "dias_para_termino": dias_para_termino,
        "dias_vencido": abs(dias_para_termino) if dias_para_termino is not None and dias_para_termino < 0 else 0,
        "dias_sin_movimiento": dias_sin_movimiento,
        "is_overdue": is_overdue_sla or (dias_para_termino is not None and dias_para_termino < 0),
        "is_critical": (
            dias_para_termino is not None and dias_para_termino <= CRITICAL_WINDOW_DAYS
        ) or _is_critical_by_status(estatus_name) or is_critical_sla,
        "is_stale": dias_sin_movimiento >= STALE_WINDOW_DAYS,
        "priority_score": score,
        "priority_label": priority_label,
        "priority_class": _priority_class(priority_label),
        "sla_semaforo": semaforo or "gris",
        "sla_semaforo_label": (sla_snapshot or {}).get("semaforo_label", "Sin SLA"),
        "sla_riesgo_label": (sla_snapshot or {}).get("riesgo_label", "Bajo"),
        "sla_escalamiento_aplica": bool((sla_snapshot or {}).get("escalamiento_aplica")),
        "cct": caso.cct_id,
        "cct_nombre": caso.cct_nombre,
        "updated_at": caso.actualizado_en,
        "detail_url": reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk}),
    }


def _to_tramite_item(
    tramite: models.TramiteCaso,
    *,
    today,
    now,
    sla_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fecha_limite = None
    dias_para_termino = None
    if sla_snapshot:
        fecha_limite = sla_snapshot.get("fecha_vencimiento")
        dias_para_termino = sla_snapshot.get("dias_restantes")
    if fecha_limite is None:
        fecha_limite = tramite.fecha_termino or tramite.incidencia_fecha_termino
    if dias_para_termino is None and fecha_limite:
        dias_para_termino = (fecha_limite - today).days
    dias_sin_movimiento = max((now - tramite.actualizado_en).days, 0)
    estatus_name = getattr(tramite.estatus, "nombre", "") or "Sin estatus"
    score = int((sla_snapshot or {}).get("riesgo_score") or 0)
    if not score:
        score = _priority_score(
            dias_para_termino=dias_para_termino,
            dias_sin_movimiento=dias_sin_movimiento,
            status_name=estatus_name,
        ) + 2
    if dias_sin_movimiento >= STALE_WINDOW_DAYS:
        score += 8
    priority_label = _priority_label(score)
    semaforo = (sla_snapshot or {}).get("semaforo")
    is_critical_sla = semaforo in {"amarillo", "rojo"}
    is_overdue_sla = semaforo == "rojo"
    return {
        "tipo": "tramite",
        "id": tramite.pk,
        "referencia": f"Trámite #{tramite.pk}",
        "caso_id": tramite.caso_id,
        "tramite_id": tramite.pk,
        "expediente": (tramite.numero_oficio or "").strip() or "Sin expediente",
        "asunto": (tramite.asunto or "").strip(),
        "estatus": estatus_name,
        "fecha_limite": fecha_limite,
        "dias_para_termino": dias_para_termino,
        "dias_vencido": abs(dias_para_termino) if dias_para_termino is not None and dias_para_termino < 0 else 0,
        "dias_sin_movimiento": dias_sin_movimiento,
        "is_overdue": is_overdue_sla or (dias_para_termino is not None and dias_para_termino < 0),
        "is_critical": (
            dias_para_termino is not None and dias_para_termino <= CRITICAL_WINDOW_DAYS
        ) or _is_critical_by_status(estatus_name) or is_critical_sla,
        "is_stale": dias_sin_movimiento >= STALE_WINDOW_DAYS,
        "priority_score": score,
        "priority_label": priority_label,
        "priority_class": _priority_class(priority_label),
        "sla_semaforo": semaforo or "gris",
        "sla_semaforo_label": (sla_snapshot or {}).get("semaforo_label", "Sin SLA"),
        "sla_riesgo_label": (sla_snapshot or {}).get("riesgo_label", "Bajo"),
        "sla_escalamiento_aplica": bool((sla_snapshot or {}).get("escalamiento_aplica")),
        "cct": tramite.cct_id or getattr(tramite.caso, "cct_id", ""),
        "cct_nombre": tramite.cct_nombre or getattr(tramite.caso, "cct_nombre", ""),
        "updated_at": tramite.actualizado_en,
        "detail_url": reverse(
            "tramites:tramite-caso-detail",
            kwargs={"caso_pk": tramite.caso_id, "pk": tramite.pk},
        ),
    }


def _sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    dias_para_termino = (
        item.get("dias_para_termino")
        if item.get("dias_para_termino") is not None
        else 10_000
    )
    return (
        -int(item.get("priority_score") or 0),
        int(dias_para_termino),
        -int(item.get("dias_sin_movimiento") or 0),
        str(item.get("tipo") or ""),
        int(item.get("id") or 0),
    )


def build_user_work_items(user) -> list[dict[str, Any]]:
    if not getattr(user, "is_authenticated", False):
        return []

    casos_qs = (
        models.CasoInterno.objects.filter(
            Q(usuarios_involucrados=user) | Q(creado_por=user)
        )
        .select_related("estatus", "cct")
        .distinct()
    )
    tramites_qs = (
        models.TramiteCaso.objects.filter(
            Q(usuarios_involucrados=user)
            | Q(caso__usuarios_involucrados=user)
            | Q(caso__creado_por=user)
        )
        .select_related("estatus", "caso", "caso__cct")
        .distinct()
    )

    casos = list(casos_qs)
    tramites = list(tramites_qs)
    today = timezone.localdate()
    now = timezone.now()
    rule_index = sla.get_rule_index()
    casos_sla = sla.build_snapshots_for_casos(casos, today=today, rule_index=rule_index)
    tramites_sla = sla.build_snapshots_for_tramites(tramites, today=today, rule_index=rule_index)
    items = [
        *(
            _to_case_item(
                caso,
                today=today,
                now=now,
                sla_snapshot=casos_sla.get(caso.pk),
            )
            for caso in casos
        ),
        *(
            _to_tramite_item(
                tramite,
                today=today,
                now=now,
                sla_snapshot=tramites_sla.get(tramite.pk),
            )
            for tramite in tramites
        ),
    ]
    items.sort(key=_sort_key)
    return items


def build_user_operation_snapshot(
    user,
    *,
    queue_limit: int = 10,
    panel_limit: int = 6,
) -> dict[str, Any]:
    items = build_user_work_items(user)
    criticos = [item for item in items if item["is_critical"]]
    vencidos = [item for item in items if item["is_overdue"]]
    sin_movimiento = [item for item in items if item["is_stale"]]
    return {
        "total": len(items),
        "criticos_total": len(criticos),
        "vencidos_total": len(vencidos),
        "sin_movimiento_total": len(sin_movimiento),
        "criticos_items": criticos[:panel_limit],
        "vencidos_items": vencidos[:panel_limit],
        "sin_movimiento_items": sin_movimiento[:panel_limit],
        "queue_items": items[:queue_limit],
        "all_items": items,
        "critical_window_days": CRITICAL_WINDOW_DAYS,
        "stale_window_days": STALE_WINDOW_DAYS,
    }


def filter_queue_items(
    items: list[dict[str, Any]],
    *,
    tipo: str = "",
    prioridad: str = "",
    estado: str = "",
) -> list[dict[str, Any]]:
    filtered = items
    if tipo in {"caso", "tramite"}:
        filtered = [item for item in filtered if item["tipo"] == tipo]
    if prioridad:
        prioridad_norm = prioridad.strip().lower()
        filtered = [
            item
            for item in filtered
            if str(item.get("priority_label") or "").strip().lower() == prioridad_norm
        ]
    if estado == "criticos":
        filtered = [item for item in filtered if item["is_critical"]]
    elif estado == "vencidos":
        filtered = [item for item in filtered if item["is_overdue"]]
    elif estado == "sin-movimiento":
        filtered = [item for item in filtered if item["is_stale"]]
    return filtered
