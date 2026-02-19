from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.utils import timezone

from tramites import models
from tramites.services import auditoria


def _is_blank_or_sn(value: str | None) -> bool:
    token = (value or "").strip().upper()
    return token in {"", "S/N", "SN"}


def _issue(
    *,
    categoria: str,
    severidad: str,
    regla_codigo: str,
    titulo: str,
    descripcion: str,
    entidad_tipo: str,
    entidad_id: int,
    metadata: dict[str, Any] | None = None,
    caso_id: int | None = None,
    tramite_id: int | None = None,
    licencia_id: int | None = None,
) -> dict[str, Any]:
    return {
        "categoria": categoria,
        "severidad": severidad,
        "regla_codigo": regla_codigo,
        "titulo": titulo,
        "descripcion": descripcion,
        "entidad_tipo": entidad_tipo,
        "entidad_id": entidad_id,
        "metadata": metadata or {},
        "caso_id": caso_id,
        "tramite_id": tramite_id,
        "licencia_id": licencia_id,
    }


def _collect_incomplete_issues() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    casos = models.CasoInterno.objects.filter(
        Q(numero_oficio__isnull=True)
        | Q(numero_oficio__exact="")
        | Q(numero_oficio__iexact="S/N")
        | Q(numero_oficio__iexact="SN")
        | Q(asunto__isnull=True)
        | Q(asunto__exact="")
        | Q(estatus__isnull=True)
    ).only("id", "numero_oficio", "asunto", "estatus_id", "cct_nombre")
    for caso in casos:
        if _is_blank_or_sn(caso.numero_oficio):
            issues.append(
                _issue(
                    categoria="incompleto",
                    severidad="media",
                    regla_codigo="caso.sin_expediente",
                    titulo="Caso sin número de expediente válido",
                    descripcion="Captura un número de expediente distinto de S/N.",
                    entidad_tipo="caso",
                    entidad_id=caso.pk,
                    caso_id=caso.pk,
                )
            )
        if not (caso.asunto or "").strip():
            issues.append(
                _issue(
                    categoria="incompleto",
                    severidad="baja",
                    regla_codigo="caso.sin_asunto",
                    titulo="Caso sin asunto",
                    descripcion="Define el asunto para facilitar búsqueda y seguimiento.",
                    entidad_tipo="caso",
                    entidad_id=caso.pk,
                    caso_id=caso.pk,
                )
            )
        if caso.estatus_id is None:
            issues.append(
                _issue(
                    categoria="incompleto",
                    severidad="alta",
                    regla_codigo="caso.sin_estatus",
                    titulo="Caso sin estatus",
                    descripcion="Asigna estatus inicial para mantener trazabilidad.",
                    entidad_tipo="caso",
                    entidad_id=caso.pk,
                    caso_id=caso.pk,
                )
            )

    tramites = models.TramiteCaso.objects.filter(
        Q(numero_oficio__isnull=True)
        | Q(numero_oficio__exact="")
        | Q(numero_oficio__iexact="S/N")
        | Q(numero_oficio__iexact="SN")
        | Q(asunto__isnull=True)
        | Q(asunto__exact="")
        | Q(estatus__isnull=True)
    ).only("id", "numero_oficio", "asunto", "estatus_id", "caso_id")
    for tramite in tramites:
        if _is_blank_or_sn(tramite.numero_oficio):
            issues.append(
                _issue(
                    categoria="incompleto",
                    severidad="media",
                    regla_codigo="tramite.sin_expediente",
                    titulo="Trámite sin número de expediente válido",
                    descripcion="Captura un número de expediente distinto de S/N.",
                    entidad_tipo="tramite",
                    entidad_id=tramite.pk,
                    caso_id=tramite.caso_id,
                    tramite_id=tramite.pk,
                )
            )
        if not (tramite.asunto or "").strip():
            issues.append(
                _issue(
                    categoria="incompleto",
                    severidad="baja",
                    regla_codigo="tramite.sin_asunto",
                    titulo="Trámite sin asunto",
                    descripcion="Define el asunto para dar contexto al seguimiento.",
                    entidad_tipo="tramite",
                    entidad_id=tramite.pk,
                    caso_id=tramite.caso_id,
                    tramite_id=tramite.pk,
                )
            )
        if tramite.estatus_id is None:
            issues.append(
                _issue(
                    categoria="incompleto",
                    severidad="alta",
                    regla_codigo="tramite.sin_estatus",
                    titulo="Trámite sin estatus",
                    descripcion="Asigna estatus para habilitar trazabilidad del anexo.",
                    entidad_tipo="tramite",
                    entidad_id=tramite.pk,
                    caso_id=tramite.caso_id,
                    tramite_id=tramite.pk,
                )
            )

    licencias = models.LicenciaRegistro.objects.filter(
        Q(numero_expediente__isnull=True)
        | Q(numero_expediente__exact="")
        | Q(estatus__isnull=True)
    ).only("id", "numero_expediente", "estatus_id")
    for licencia in licencias:
        if _is_blank_or_sn(licencia.numero_expediente):
            issues.append(
                _issue(
                    categoria="incompleto",
                    severidad="media",
                    regla_codigo="licencia.sin_expediente",
                    titulo="Licencia sin expediente",
                    descripcion="Completa el número de expediente de la licencia.",
                    entidad_tipo="licencia",
                    entidad_id=licencia.pk,
                    licencia_id=licencia.pk,
                )
            )
        if licencia.estatus_id is None:
            issues.append(
                _issue(
                    categoria="incompleto",
                    severidad="alta",
                    regla_codigo="licencia.sin_estatus",
                    titulo="Licencia sin estatus",
                    descripcion="Asigna estatus para controlar el flujo de licencias.",
                    entidad_tipo="licencia",
                    entidad_id=licencia.pk,
                    licencia_id=licencia.pk,
                )
            )

    return issues


def _collect_duplicate_issues() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    casos_dup = (
        models.CasoInterno.objects.exclude(numero_oficio__isnull=True)
        .exclude(numero_oficio__exact="")
        .exclude(numero_oficio__iexact="S/N")
        .exclude(numero_oficio__iexact="SN")
        .values("numero_oficio")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    for row in casos_dup:
        numero = row["numero_oficio"]
        ids = list(models.CasoInterno.objects.filter(numero_oficio=numero).values_list("id", flat=True))
        for caso_id in ids:
            issues.append(
                _issue(
                    categoria="duplicado",
                    severidad="alta",
                    regla_codigo="caso.expediente_duplicado",
                    titulo="Caso con expediente duplicado",
                    descripcion=f"El expediente {numero} aparece en múltiples casos.",
                    entidad_tipo="caso",
                    entidad_id=caso_id,
                    metadata={"expediente": numero, "ids_relacionados": ids},
                    caso_id=caso_id,
                )
            )

    tramites_dup = (
        models.TramiteCaso.objects.exclude(numero_oficio__isnull=True)
        .exclude(numero_oficio__exact="")
        .exclude(numero_oficio__iexact="S/N")
        .exclude(numero_oficio__iexact="SN")
        .values("numero_oficio")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    for row in tramites_dup:
        numero = row["numero_oficio"]
        items = list(
            models.TramiteCaso.objects.filter(numero_oficio=numero).values_list("id", "caso_id")
        )
        ids = [item[0] for item in items]
        for tramite_id, caso_id in items:
            issues.append(
                _issue(
                    categoria="duplicado",
                    severidad="alta",
                    regla_codigo="tramite.expediente_duplicado",
                    titulo="Trámite con expediente duplicado",
                    descripcion=f"El expediente {numero} aparece en múltiples trámites.",
                    entidad_tipo="tramite",
                    entidad_id=tramite_id,
                    metadata={"expediente": numero, "ids_relacionados": ids},
                    caso_id=caso_id,
                    tramite_id=tramite_id,
                )
            )

    licencias_dup = (
        models.LicenciaRegistro.objects.exclude(numero_expediente__isnull=True)
        .exclude(numero_expediente__exact="")
        .values("numero_expediente")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    for row in licencias_dup:
        numero = row["numero_expediente"]
        ids = list(
            models.LicenciaRegistro.objects.filter(numero_expediente=numero).values_list("id", flat=True)
        )
        for licencia_id in ids:
            issues.append(
                _issue(
                    categoria="duplicado",
                    severidad="alta",
                    regla_codigo="licencia.expediente_duplicado",
                    titulo="Licencia con expediente duplicado",
                    descripcion=f"El expediente {numero} se repite en licencias.",
                    entidad_tipo="licencia",
                    entidad_id=licencia_id,
                    metadata={"expediente": numero, "ids_relacionados": ids},
                    licencia_id=licencia_id,
                )
            )

    return issues


def _collect_inconsistent_issues() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    casos_fechas = models.CasoInterno.objects.filter(
        fecha_termino__isnull=False,
        fecha_termino__lt=F("fecha_apertura"),
    ).only("id", "fecha_apertura", "fecha_termino")
    for caso in casos_fechas:
        issues.append(
            _issue(
                categoria="inconsistente",
                severidad="alta",
                regla_codigo="caso.rango_fechas_invalido",
                titulo="Caso con rango de fechas inconsistente",
                descripcion="La fecha de término es anterior a la fecha de apertura.",
                entidad_tipo="caso",
                entidad_id=caso.pk,
                metadata={
                    "fecha_apertura": caso.fecha_apertura.isoformat() if caso.fecha_apertura else "",
                    "fecha_termino": caso.fecha_termino.isoformat() if caso.fecha_termino else "",
                },
                caso_id=caso.pk,
            )
        )

    tramites_fechas = models.TramiteCaso.objects.filter(
        fecha_termino__isnull=False,
        fecha_termino__lt=F("fecha"),
    ).only("id", "caso_id", "fecha", "fecha_termino")
    for tramite in tramites_fechas:
        issues.append(
            _issue(
                categoria="inconsistente",
                severidad="alta",
                regla_codigo="tramite.rango_fechas_invalido",
                titulo="Trámite con rango de fechas inconsistente",
                descripcion="La fecha de término es anterior a la fecha del trámite.",
                entidad_tipo="tramite",
                entidad_id=tramite.pk,
                metadata={
                    "fecha_tramite": tramite.fecha.isoformat() if tramite.fecha else "",
                    "fecha_termino": tramite.fecha_termino.isoformat() if tramite.fecha_termino else "",
                },
                caso_id=tramite.caso_id,
                tramite_id=tramite.pk,
            )
        )

    ultimo_estatus_caso = (
        models.HistorialEstatusCaso.objects.filter(caso_id=OuterRef("pk"))
        .order_by("-fecha_cambio", "-id")
        .values("estatus_nuevo_id")[:1]
    )
    casos_estatus = (
        models.CasoInterno.objects.annotate(estatus_historial_id=Subquery(ultimo_estatus_caso))
        .exclude(estatus_historial_id__isnull=True)
        .exclude(estatus_id=F("estatus_historial_id"))
        .only("id", "estatus_id")
    )
    for caso in casos_estatus:
        issues.append(
            _issue(
                categoria="inconsistente",
                severidad="media",
                regla_codigo="caso.estatus_fuera_historial",
                titulo="Caso con estatus fuera de historial",
                descripcion="El estatus actual no coincide con el último estatus del historial.",
                entidad_tipo="caso",
                entidad_id=caso.pk,
                metadata={"estatus_actual_id": caso.estatus_id, "estatus_historial_id": caso.estatus_historial_id},
                caso_id=caso.pk,
            )
        )

    ultimo_estatus_tramite = (
        models.HistorialEstatusTramiteCaso.objects.filter(tramite_id=OuterRef("pk"))
        .order_by("-fecha_cambio", "-id")
        .values("estatus_nuevo_id")[:1]
    )
    tramites_estatus = (
        models.TramiteCaso.objects.annotate(estatus_historial_id=Subquery(ultimo_estatus_tramite))
        .exclude(estatus_historial_id__isnull=True)
        .exclude(estatus_id=F("estatus_historial_id"))
        .only("id", "caso_id", "estatus_id")
    )
    for tramite in tramites_estatus:
        issues.append(
            _issue(
                categoria="inconsistente",
                severidad="media",
                regla_codigo="tramite.estatus_fuera_historial",
                titulo="Trámite con estatus fuera de historial",
                descripcion="El estatus actual no coincide con el último estatus del historial.",
                entidad_tipo="tramite",
                entidad_id=tramite.pk,
                metadata={
                    "estatus_actual_id": tramite.estatus_id,
                    "estatus_historial_id": tramite.estatus_historial_id,
                },
                caso_id=tramite.caso_id,
                tramite_id=tramite.pk,
            )
        )

    ultimo_estatus_licencia = (
        models.HistorialEstatusLicencia.objects.filter(licencia_id=OuterRef("pk"))
        .order_by("-fecha_cambio", "-id")
        .values("estatus_nuevo_id")[:1]
    )
    licencias_estatus = (
        models.LicenciaRegistro.objects.annotate(estatus_historial_id=Subquery(ultimo_estatus_licencia))
        .exclude(estatus_historial_id__isnull=True)
        .exclude(estatus_id=F("estatus_historial_id"))
        .only("id", "estatus_id")
    )
    for licencia in licencias_estatus:
        issues.append(
            _issue(
                categoria="inconsistente",
                severidad="media",
                regla_codigo="licencia.estatus_fuera_historial",
                titulo="Licencia con estatus fuera de historial",
                descripcion="El estatus actual no coincide con el último estatus del historial.",
                entidad_tipo="licencia",
                entidad_id=licencia.pk,
                metadata={
                    "estatus_actual_id": licencia.estatus_id,
                    "estatus_historial_id": licencia.estatus_historial_id,
                },
                licencia_id=licencia.pk,
            )
        )

    return issues


def _persist_issues(run: models.DataQualityRun, issues: list[dict[str, Any]]) -> tuple[int, int]:
    seen_ids: list[int] = []
    now = timezone.now()

    for issue in issues:
        defaults = {
            "severidad": issue["severidad"],
            "titulo": issue["titulo"],
            "descripcion": issue["descripcion"],
            "metadata": issue.get("metadata") or {},
            "activo": True,
            "resuelto_en": None,
            "ultima_corrida": run,
            "caso_id": issue.get("caso_id"),
            "tramite_id": issue.get("tramite_id"),
            "licencia_id": issue.get("licencia_id"),
            "ultimo_detectado_en": now,
        }
        obj, _ = models.DataQualityIssue.objects.update_or_create(
            categoria=issue["categoria"],
            regla_codigo=issue["regla_codigo"],
            entidad_tipo=issue["entidad_tipo"],
            entidad_id=issue["entidad_id"],
            defaults=defaults,
        )
        seen_ids.append(obj.pk)

    stale_qs = models.DataQualityIssue.objects.filter(activo=True)
    if seen_ids:
        stale_qs = stale_qs.exclude(pk__in=seen_ids)
    resolved_count = stale_qs.update(activo=False, resuelto_en=now, ultima_corrida=run)
    return len(seen_ids), resolved_count


def run_quality_scan(
    *,
    actor=None,
    origen: str = "manual",
    async_job: models.AsyncJob | None = None,
) -> models.DataQualityRun:
    run = models.DataQualityRun.objects.create(
        origen=origen,
        estado="ejecutando",
        ejecutado_por=actor if getattr(actor, "is_authenticated", False) else None,
        async_job=async_job,
    )

    try:
        with transaction.atomic():
            issues: list[dict[str, Any]] = []
            issues.extend(_collect_incomplete_issues())
            issues.extend(_collect_duplicate_issues())
            issues.extend(_collect_inconsistent_issues())
            detected_count, resolved_count = _persist_issues(run, issues)

            activos = list(
                models.DataQualityIssue.objects.filter(activo=True)
                .values("categoria")
                .annotate(total=Count("id"))
                .order_by("categoria")
            )
            activos_por_categoria = {item["categoria"]: item["total"] for item in activos}
            run.estado = "exitoso"
            run.finalizado_en = timezone.now()
            run.resumen = {
                "issues_detected": detected_count,
                "issues_resolved": resolved_count,
                "issues_active_total": sum(activos_por_categoria.values()),
                "issues_active_by_category": activos_por_categoria,
            }
            run.save(update_fields=["estado", "finalizado_en", "resumen"])
    except Exception as exc:  # pragma: no cover - defensivo
        run.estado = "error"
        run.finalizado_en = timezone.now()
        run.error = str(exc)
        run.save(update_fields=["estado", "finalizado_en", "error"])
        auditoria.registrar_evento(
            categoria="calidad_datos",
            accion="error",
            descripcion="Error en corrida de calidad de datos",
            detalle=str(exc),
            actor=actor,
            instancia=run,
        )
        raise

    auditoria.registrar_cambio_critico(
        modulo="calidad_datos",
        accion="ejecutado",
        descripcion="Corrida de calidad de datos completada",
        despues=run.resumen,
        actor=actor,
        instancia=run,
    )
    return run


def get_latest_report(*, issue_limit: int = 200):
    latest_run = models.DataQualityRun.objects.select_related("ejecutado_por").order_by("-iniciado_en").first()
    active_issues_qs = (
        models.DataQualityIssue.objects.filter(activo=True)
        .select_related("caso", "tramite", "licencia", "ultima_corrida")
        .order_by("-severidad", "-ultimo_detectado_en", "-id")
    )
    if issue_limit:
        active_issues_qs = active_issues_qs[:issue_limit]
    summary = {
        "total_activos": models.DataQualityIssue.objects.filter(activo=True).count(),
        "incompletos": models.DataQualityIssue.objects.filter(activo=True, categoria="incompleto").count(),
        "duplicados": models.DataQualityIssue.objects.filter(activo=True, categoria="duplicado").count(),
        "inconsistentes": models.DataQualityIssue.objects.filter(activo=True, categoria="inconsistente").count(),
    }
    return latest_run, active_issues_qs, summary

