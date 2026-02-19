from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from tramites import inbox, models
from tramites.services import auditoria


User = get_user_model()

DEFAULT_WARNING_DAYS = 2
CLOSED_STATUS_KEYWORDS = ("concluido", "cerrado", "finalizado", "cancelado")
SEMAFORO_LABELS = {
    "verde": "Verde",
    "amarillo": "Amarillo",
    "rojo": "Rojo",
    "gris": "Sin SLA",
}


@dataclass(frozen=True)
class SLARuleIndex:
    case_status: dict[tuple[int, int], models.SLARegla]
    case_base: dict[int, models.SLARegla]
    tramite_status: dict[tuple[int, int], models.SLARegla]
    tramite_base: dict[int, models.SLARegla]


def _status_is_closed(status_name: str) -> bool:
    normalized = (status_name or "").strip().lower()
    return any(keyword in normalized for keyword in CLOSED_STATUS_KEYWORDS)


def _usuarios_union(*groups: Iterable[User]) -> list[User]:
    seen_ids: set[int] = set()
    result: list[User] = []
    for group in groups:
        for user in group:
            if not user or not user.is_active:
                continue
            if user.pk in seen_ids:
                continue
            seen_ids.add(user.pk)
            result.append(user)
    return result


def get_rule_index(*, include_inactive: bool = False) -> SLARuleIndex:
    rules_qs = (
        models.SLARegla.objects.select_related(
            "tipo_proceso",
            "estatus_caso",
            "estatus_tramite",
            "grupo_escalamiento",
        )
        .prefetch_related("grupo_escalamiento__user_set")
        .order_by("ambito", "tipo_proceso_id", "orden", "id")
    )
    if not include_inactive:
        rules_qs = rules_qs.filter(esta_activa=True)
    rules = list(rules_qs)

    case_status: dict[tuple[int, int], models.SLARegla] = {}
    case_base: dict[int, models.SLARegla] = {}
    tramite_status: dict[tuple[int, int], models.SLARegla] = {}
    tramite_base: dict[int, models.SLARegla] = {}

    for rule in rules:
        if rule.ambito == models.SLARegla.AMBITO_CASO:
            if rule.estatus_caso_id:
                case_status[(rule.tipo_proceso_id, rule.estatus_caso_id)] = rule
            else:
                case_base[rule.tipo_proceso_id] = rule
            continue
        if rule.estatus_tramite_id:
            tramite_status[(rule.tipo_proceso_id, rule.estatus_tramite_id)] = rule
        else:
            tramite_base[rule.tipo_proceso_id] = rule

    return SLARuleIndex(
        case_status=case_status,
        case_base=case_base,
        tramite_status=tramite_status,
        tramite_base=tramite_base,
    )


def _resolve_rule_for_case(caso: models.CasoInterno, rule_index: SLARuleIndex) -> models.SLARegla | None:
    if caso.tipo_inicial_id and caso.estatus_id:
        specific = rule_index.case_status.get((caso.tipo_inicial_id, caso.estatus_id))
        if specific is not None:
            return specific
    if caso.tipo_inicial_id:
        return rule_index.case_base.get(caso.tipo_inicial_id)
    return None


def _resolve_rule_for_tramite(
    tramite: models.TramiteCaso,
    rule_index: SLARuleIndex,
) -> models.SLARegla | None:
    if tramite.tipo_id and tramite.estatus_id:
        specific = rule_index.tramite_status.get((tramite.tipo_id, tramite.estatus_id))
        if specific is not None:
            return specific
    if tramite.tipo_id:
        return rule_index.tramite_base.get(tramite.tipo_id)
    return None


def _legacy_due_date(obj: models.CasoInterno | models.TramiteCaso) -> date | None:
    return obj.fecha_termino or obj.incidencia_fecha_termino


def _risk_from_snapshot(
    *,
    rule: models.SLARegla | None,
    semaforo: str,
    dias_restantes: int | None,
) -> tuple[int, str, str]:
    base = int(getattr(rule, "peso_riesgo", 40) or 40)
    if semaforo == "rojo":
        atraso = abs(dias_restantes or 0)
        score = base + 70 + min(atraso * 3, 40)
    elif semaforo == "amarillo":
        urgencia = max((getattr(rule, "dias_alerta_amarilla", DEFAULT_WARNING_DAYS) or DEFAULT_WARNING_DAYS) - (dias_restantes or 0), 0)
        score = base + 35 + min(urgencia * 5, 25)
    elif semaforo == "verde":
        margen = max(dias_restantes or 0, 0)
        score = max(base - min(margen, 35), 10)
    else:
        score = max(base - 20, 10)

    if score >= 130:
        return score, "Crítico", "critica"
    if score >= 95:
        return score, "Alto", "alta"
    if score >= 60:
        return score, "Medio", "media"
    return score, "Bajo", "normal"


def _build_snapshot(
    *,
    ambito: str,
    entity_id: int,
    estatus_nombre: str,
    fecha_referencia: date | None,
    legacy_vencimiento: date | None,
    rule: models.SLARegla | None,
    today: date,
) -> dict[str, Any]:
    fecha_vencimiento = legacy_vencimiento
    source = "legacy_fecha_termino" if legacy_vencimiento else "sin_regla"
    if rule and fecha_referencia:
        fecha_vencimiento = fecha_referencia + timedelta(days=int(rule.dias_objetivo or 0))
        source = "sla"
    dias_restantes = (fecha_vencimiento - today).days if fecha_vencimiento else None

    if dias_restantes is None:
        semaforo = "gris"
    elif dias_restantes < 0:
        semaforo = "rojo"
    else:
        warning_days = int(getattr(rule, "dias_alerta_amarilla", DEFAULT_WARNING_DAYS) or DEFAULT_WARNING_DAYS)
        semaforo = "amarillo" if dias_restantes <= warning_days else "verde"

    riesgo_score, riesgo_label, riesgo_class = _risk_from_snapshot(
        rule=rule,
        semaforo=semaforo,
        dias_restantes=dias_restantes,
    )
    dias_vencido = abs(dias_restantes) if dias_restantes is not None and dias_restantes < 0 else 0
    escalamiento_aplica = bool(
        rule
        and rule.grupo_escalamiento_id
        and dias_restantes is not None
        and dias_restantes < 0
        and dias_vencido >= int(rule.dias_escalamiento or 0)
    )

    return {
        "ambito": ambito,
        "entity_id": entity_id,
        "has_rule": bool(rule),
        "rule_id": getattr(rule, "pk", None),
        "rule_name": str(rule) if rule else "",
        "fecha_referencia": fecha_referencia,
        "fecha_vencimiento": fecha_vencimiento,
        "dias_restantes": dias_restantes,
        "dias_vencido": dias_vencido,
        "semaforo": semaforo,
        "semaforo_label": SEMAFORO_LABELS.get(semaforo, "Sin SLA"),
        "semaforo_class": semaforo,
        "riesgo_score": riesgo_score,
        "riesgo_label": riesgo_label,
        "riesgo_class": riesgo_class,
        "es_critico": semaforo in {"amarillo", "rojo"},
        "es_vencido": semaforo == "rojo",
        "escalamiento_aplica": escalamiento_aplica,
        "dias_escalamiento": int(rule.dias_escalamiento) if rule else None,
        "source": source,
        "estatus_cerrado": _status_is_closed(estatus_nombre),
    }


def build_sla_snapshot_for_case(
    caso: models.CasoInterno,
    *,
    today: date | None = None,
    rule_index: SLARuleIndex | None = None,
) -> dict[str, Any]:
    today = today or timezone.localdate()
    rule_index = rule_index or get_rule_index()
    rule = _resolve_rule_for_case(caso, rule_index)
    return _build_snapshot(
        ambito=models.SLARegla.AMBITO_CASO,
        entity_id=caso.pk,
        estatus_nombre=getattr(caso.estatus, "nombre", ""),
        fecha_referencia=caso.fecha_apertura,
        legacy_vencimiento=_legacy_due_date(caso),
        rule=rule,
        today=today,
    )


def build_sla_snapshot_for_tramite(
    tramite: models.TramiteCaso,
    *,
    today: date | None = None,
    rule_index: SLARuleIndex | None = None,
) -> dict[str, Any]:
    today = today or timezone.localdate()
    rule_index = rule_index or get_rule_index()
    rule = _resolve_rule_for_tramite(tramite, rule_index)
    return _build_snapshot(
        ambito=models.SLARegla.AMBITO_TRAMITE,
        entity_id=tramite.pk,
        estatus_nombre=getattr(tramite.estatus, "nombre", ""),
        fecha_referencia=tramite.fecha,
        legacy_vencimiento=_legacy_due_date(tramite),
        rule=rule,
        today=today,
    )


def build_snapshots_for_casos(
    casos: Iterable[models.CasoInterno],
    *,
    today: date | None = None,
    rule_index: SLARuleIndex | None = None,
) -> dict[int, dict[str, Any]]:
    casos_list = [caso for caso in casos if caso is not None]
    if not casos_list:
        return {}
    today = today or timezone.localdate()
    rule_index = rule_index or get_rule_index()
    return {
        caso.pk: build_sla_snapshot_for_case(caso, today=today, rule_index=rule_index)
        for caso in casos_list
    }


def build_snapshots_for_tramites(
    tramites: Iterable[models.TramiteCaso],
    *,
    today: date | None = None,
    rule_index: SLARuleIndex | None = None,
) -> dict[int, dict[str, Any]]:
    tramites_list = [tramite for tramite in tramites if tramite is not None]
    if not tramites_list:
        return {}
    today = today or timezone.localdate()
    rule_index = rule_index or get_rule_index()
    return {
        tramite.pk: build_sla_snapshot_for_tramite(tramite, today=today, rule_index=rule_index)
        for tramite in tramites_list
    }


def _usuarios_objetivo_caso(caso: models.CasoInterno) -> list[User]:
    return list(caso.usuarios_involucrados.filter(is_active=True))


def _usuarios_objetivo_tramite(tramite: models.TramiteCaso) -> list[User]:
    usuarios = list(tramite.usuarios_involucrados.filter(is_active=True))
    if usuarios:
        return usuarios
    return _usuarios_objetivo_caso(tramite.caso)


def _usuarios_escalamiento(rule: models.SLARegla | None) -> list[User]:
    if not rule or not rule.grupo_escalamiento_id:
        return []
    return list(rule.grupo_escalamiento.user_set.filter(is_active=True))


def _referencia_objetivo(
    *,
    caso: models.CasoInterno | None = None,
    tramite: models.TramiteCaso | None = None,
) -> str:
    if tramite is not None:
        expediente = (tramite.numero_oficio or "").strip() or f"Trámite #{tramite.pk}"
        return f"{expediente} · Caso #{tramite.caso_id}"
    expediente = (caso.numero_oficio or "").strip() or f"Caso #{caso.pk}"
    return expediente


def _registrar_alerta_unica(
    *,
    tipo_alerta: str,
    snapshot: dict[str, Any],
    regla: models.SLARegla | None,
    async_job: models.AsyncJob | None,
    caso: models.CasoInterno | None = None,
    tramite: models.TramiteCaso | None = None,
) -> bool:
    fecha_vencimiento = snapshot.get("fecha_vencimiento")
    if not fecha_vencimiento:
        return False
    lookup = {
        "tipo_alerta": tipo_alerta,
        "fecha_vencimiento": fecha_vencimiento,
    }
    if caso is not None:
        lookup["caso"] = caso
    else:
        lookup["tramite"] = tramite
    defaults = {
        "regla": regla,
        "dias_restantes": snapshot.get("dias_restantes"),
        "metadata": {
            "semaforo": snapshot.get("semaforo"),
            "riesgo_score": snapshot.get("riesgo_score"),
            "source": snapshot.get("source"),
        },
        "async_job": async_job,
    }
    try:
        with transaction.atomic():
            _, created = models.SLAAlertaRegistro.objects.get_or_create(
                **lookup,
                defaults=defaults,
            )
        return created
    except IntegrityError:
        return False


def _emitir_alerta(
    *,
    tipo_alerta: str,
    snapshot: dict[str, Any],
    usuarios: list[User],
    regla: models.SLARegla | None,
    async_job: models.AsyncJob | None,
    actor,
    caso: models.CasoInterno | None = None,
    tramite: models.TramiteCaso | None = None,
) -> bool:
    if not usuarios:
        return False
    was_created = _registrar_alerta_unica(
        tipo_alerta=tipo_alerta,
        snapshot=snapshot,
        regla=regla,
        async_job=async_job,
        caso=caso,
        tramite=tramite,
    )
    if not was_created:
        return False

    referencia = _referencia_objetivo(caso=caso, tramite=tramite)
    fecha_vencimiento = snapshot.get("fecha_vencimiento")
    dias_restantes = snapshot.get("dias_restantes")
    dias_vencido = snapshot.get("dias_vencido")

    if tipo_alerta == models.SLAAlertaRegistro.ALERTA_AMARILLA:
        titulo = f"SLA en riesgo · {referencia}"
        mensaje = (
            f"Vence el {fecha_vencimiento:%d/%m/%Y}. "
            f"Quedan {dias_restantes} día(s). "
            f"Riesgo: {snapshot.get('riesgo_label', 'Medio')}."
        )
        inbox.notificar_sla_alerta(
            titulo=titulo,
            mensaje=mensaje,
            usuarios=usuarios,
            actor=actor,
            caso=caso,
            tramite=tramite,
            referencia=referencia,
        )
        descripcion_evento = "Alerta SLA amarilla generada"
    elif tipo_alerta == models.SLAAlertaRegistro.ALERTA_ROJA:
        titulo = f"SLA vencido · {referencia}"
        mensaje = (
            f"Venció el {fecha_vencimiento:%d/%m/%Y}. "
            f"Atraso acumulado: {dias_vencido} día(s). "
            f"Riesgo: {snapshot.get('riesgo_label', 'Crítico')}."
        )
        inbox.notificar_sla_alerta(
            titulo=titulo,
            mensaje=mensaje,
            usuarios=usuarios,
            actor=actor,
            caso=caso,
            tramite=tramite,
            referencia=referencia,
        )
        descripcion_evento = "Alerta SLA roja generada"
    else:
        grupo = getattr(regla, "grupo_escalamiento", None)
        grupo_label = getattr(grupo, "name", "Rol no definido")
        titulo = f"Escalamiento SLA · {referencia}"
        mensaje = (
            f"Atraso acumulado: {dias_vencido} día(s). "
            f"Escalado a: {grupo_label}."
        )
        inbox.notificar_sla_escalamiento(
            titulo=titulo,
            mensaje=mensaje,
            usuarios=usuarios,
            actor=actor,
            caso=caso,
            tramite=tramite,
            referencia=referencia,
        )
        descripcion_evento = "Escalamiento SLA generado"

    auditoria.registrar_evento(
        categoria="sistema",
        accion="creado",
        descripcion=descripcion_evento,
        detalle=mensaje,
        metadata={
            "tipo_alerta": tipo_alerta,
            "semaforo": snapshot.get("semaforo"),
            "riesgo_score": snapshot.get("riesgo_score"),
            "fecha_vencimiento": fecha_vencimiento.isoformat() if fecha_vencimiento else None,
            "rule_id": getattr(regla, "pk", None),
            "job_id": getattr(async_job, "pk", None),
        },
        actor=actor,
        instancia=tramite if tramite is not None else caso,
    )
    return True


def _procesar_alertas_objetivo(
    *,
    snapshot: dict[str, Any],
    regla: models.SLARegla | None,
    usuarios_base: list[User],
    async_job: models.AsyncJob | None,
    actor,
    counters: dict[str, int],
    caso: models.CasoInterno | None = None,
    tramite: models.TramiteCaso | None = None,
) -> None:
    if not snapshot.get("fecha_vencimiento"):
        counters["sin_vencimiento"] += 1
        return
    if snapshot.get("estatus_cerrado"):
        counters["cerrados_omitidos"] += 1
        return

    semaforo = snapshot.get("semaforo")
    if semaforo == "amarillo":
        if _emitir_alerta(
            tipo_alerta=models.SLAAlertaRegistro.ALERTA_AMARILLA,
            snapshot=snapshot,
            usuarios=usuarios_base,
            regla=regla,
            async_job=async_job,
            actor=actor,
            caso=caso,
            tramite=tramite,
        ):
            counters["alertas_amarillas"] += 1
        else:
            counters["duplicadas_o_sin_destino"] += 1
        return

    if semaforo != "rojo":
        counters["sin_alerta"] += 1
        return

    if _emitir_alerta(
        tipo_alerta=models.SLAAlertaRegistro.ALERTA_ROJA,
        snapshot=snapshot,
        usuarios=usuarios_base,
        regla=regla,
        async_job=async_job,
        actor=actor,
        caso=caso,
        tramite=tramite,
    ):
        counters["alertas_rojas"] += 1
    else:
        counters["duplicadas_o_sin_destino"] += 1

    if not snapshot.get("escalamiento_aplica"):
        counters["sin_escalamiento"] += 1
        return

    usuarios_escalamiento = _usuarios_union(
        usuarios_base,
        _usuarios_escalamiento(regla),
    )
    if _emitir_alerta(
        tipo_alerta=models.SLAAlertaRegistro.ALERTA_ESCALAMIENTO,
        snapshot=snapshot,
        usuarios=usuarios_escalamiento,
        regla=regla,
        async_job=async_job,
        actor=actor,
        caso=caso,
        tramite=tramite,
    ):
        counters["escalamientos"] += 1
    else:
        counters["duplicadas_o_sin_destino"] += 1


def run_sla_alert_scan(
    *,
    async_job: models.AsyncJob | None = None,
    actor=None,
    now=None,
    limit: int = 2000,
) -> dict[str, Any]:
    now = now or timezone.now()
    today = timezone.localdate(now)
    if not getattr(actor, "is_authenticated", False):
        actor = getattr(async_job, "creado_por", None)

    rule_index = get_rule_index()
    casos = list(
        models.CasoInterno.objects.select_related("tipo_inicial", "estatus", "creado_por")
        .prefetch_related("usuarios_involucrados")
        .order_by("id")[:limit]
    )
    tramites = list(
        models.TramiteCaso.objects.select_related("tipo", "estatus", "caso", "caso__creado_por")
        .prefetch_related("usuarios_involucrados", "caso__usuarios_involucrados")
        .order_by("id")[:limit]
    )

    casos_snapshots = build_snapshots_for_casos(casos, today=today, rule_index=rule_index)
    tramites_snapshots = build_snapshots_for_tramites(tramites, today=today, rule_index=rule_index)
    counters = {
        "total_evaluados": len(casos) + len(tramites),
        "alertas_amarillas": 0,
        "alertas_rojas": 0,
        "escalamientos": 0,
        "sin_alerta": 0,
        "sin_vencimiento": 0,
        "sin_escalamiento": 0,
        "cerrados_omitidos": 0,
        "duplicadas_o_sin_destino": 0,
    }

    for caso in casos:
        snapshot = casos_snapshots.get(caso.pk) or {}
        rule = _resolve_rule_for_case(caso, rule_index)
        _procesar_alertas_objetivo(
            snapshot=snapshot,
            regla=rule,
            usuarios_base=_usuarios_objetivo_caso(caso),
            async_job=async_job,
            actor=actor,
            counters=counters,
            caso=caso,
        )

    for tramite in tramites:
        snapshot = tramites_snapshots.get(tramite.pk) or {}
        rule = _resolve_rule_for_tramite(tramite, rule_index)
        _procesar_alertas_objetivo(
            snapshot=snapshot,
            regla=rule,
            usuarios_base=_usuarios_objetivo_tramite(tramite),
            async_job=async_job,
            actor=actor,
            counters=counters,
            tramite=tramite,
        )

    counters["evaluado_en"] = now.isoformat()
    return counters
