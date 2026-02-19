from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Callable, Dict, Optional

from django.db import transaction
from django.utils import timezone

from tramites import models
from tramites.services import auditoria


logger = logging.getLogger(__name__)

JobHandler = Callable[[models.AsyncJob], Optional[Dict[str, Any]]]
JOB_HANDLERS: dict[str, JobHandler] = {}


def register_job_handler(job_type: str):
    def _decorator(func: JobHandler):
        JOB_HANDLERS[job_type] = func
        return func

    return _decorator


def enqueue_job(
    *,
    job_type: str,
    payload: dict[str, Any] | None = None,
    run_at=None,
    prioridad: int = 100,
    max_intentos: int = 3,
    scheduled_job: models.ScheduledJob | None = None,
    creado_por=None,
) -> models.AsyncJob:
    run_after = run_at or timezone.now()
    job = models.AsyncJob.objects.create(
        job_type=job_type,
        payload=payload or {},
        ejecutar_despues_de=run_after,
        prioridad=prioridad,
        max_intentos=max_intentos,
        scheduled_job=scheduled_job,
        creado_por=creado_por if getattr(creado_por, "is_authenticated", False) else None,
    )
    auditoria.registrar_evento(
        categoria="job",
        accion="creado",
        descripcion=f"Job encolado: {job_type}",
        metadata={
            "job_id": job.pk,
            "scheduled_job_id": scheduled_job.pk if scheduled_job else None,
            "run_at": run_after.isoformat(),
        },
        actor=creado_por,
        instancia=job,
    )
    return job


def schedule_due_jobs(*, now=None, limit: int = 100) -> list[models.AsyncJob]:
    now = now or timezone.now()
    created_jobs: list[models.AsyncJob] = []
    with transaction.atomic():
        due_schedules = list(
            models.ScheduledJob.objects.select_for_update()
            .filter(activo=True, proxima_ejecucion__lte=now)
            .order_by("proxima_ejecucion", "id")[:limit]
        )
        for scheduled in due_schedules:
            created_jobs.append(
                enqueue_job(
                    job_type=scheduled.handler,
                    payload={"scheduled_job_id": scheduled.pk, "scheduled_codigo": scheduled.codigo},
                    run_at=scheduled.proxima_ejecucion,
                    scheduled_job=scheduled,
                )
            )
            interval = max(1, int(scheduled.intervalo_minutos or 1))
            next_run = scheduled.proxima_ejecucion or now
            while next_run <= now:
                next_run = next_run + timedelta(minutes=interval)
            scheduled.proxima_ejecucion = next_run
            scheduled.ultimo_estado = "pendiente"
            scheduled.ultimo_error = ""
            scheduled.save(update_fields=["proxima_ejecucion", "ultimo_estado", "ultimo_error", "actualizado_en"])
    return created_jobs


def _claim_next_pending_job(worker_name: str) -> models.AsyncJob | None:
    now = timezone.now()
    with transaction.atomic():
        job = (
            models.AsyncJob.objects.select_for_update()
            .filter(estado="pendiente", ejecutar_despues_de__lte=now)
            .order_by("prioridad", "ejecutar_despues_de", "id")
            .first()
        )
        if job is None:
            return None
        job.estado = "ejecutando"
        job.locked_by = worker_name
        job.locked_en = now
        job.iniciado_en = now
        job.intentos = (job.intentos or 0) + 1
        job.save(
            update_fields=[
                "estado",
                "locked_by",
                "locked_en",
                "iniciado_en",
                "intentos",
            ]
        )
    return job


def _mark_schedule_result(
    scheduled_job: models.ScheduledJob | None,
    *,
    success: bool,
    error: str = "",
) -> None:
    if scheduled_job is None:
        return
    scheduled_job.ultima_ejecucion = timezone.now()
    scheduled_job.ultimo_estado = "exitoso" if success else "error"
    scheduled_job.ultimo_error = error or ""
    scheduled_job.save(update_fields=["ultima_ejecucion", "ultimo_estado", "ultimo_error", "actualizado_en"])


def run_single_job(*, worker_name: str = "worker-e1") -> models.AsyncJob | None:
    job = _claim_next_pending_job(worker_name)
    if job is None:
        return None
    handler = JOB_HANDLERS.get(job.job_type)
    if handler is None:
        job.estado = "error"
        job.error_mensaje = f"No existe handler registrado para job_type={job.job_type}"
        job.finalizado_en = timezone.now()
        job.save(update_fields=["estado", "error_mensaje", "finalizado_en"])
        _mark_schedule_result(job.scheduled_job, success=False, error=job.error_mensaje)
        auditoria.registrar_evento(
            categoria="job",
            accion="error",
            descripcion=f"Error ejecutando job {job.job_type}",
            detalle=job.error_mensaje,
            metadata={"job_id": job.pk},
            instancia=job,
        )
        return job

    try:
        result = handler(job) or {}
    except Exception as exc:  # pragma: no cover - defensivo
        logger.exception("Fallo job async id=%s type=%s", job.pk, job.job_type)
        retry = job.intentos < max(1, int(job.max_intentos or 1))
        if retry:
            delay = min(60, 2 ** max(0, job.intentos - 1))
            job.estado = "pendiente"
            job.locked_by = ""
            job.locked_en = None
            job.error_mensaje = str(exc)
            job.ejecutar_despues_de = timezone.now() + timedelta(minutes=delay)
            job.save(
                update_fields=[
                    "estado",
                    "locked_by",
                    "locked_en",
                    "error_mensaje",
                    "ejecutar_despues_de",
                ]
            )
            _mark_schedule_result(job.scheduled_job, success=False, error=str(exc))
        else:
            job.estado = "error"
            job.locked_by = ""
            job.locked_en = None
            job.error_mensaje = str(exc)
            job.finalizado_en = timezone.now()
            job.save(
                update_fields=[
                    "estado",
                    "locked_by",
                    "locked_en",
                    "error_mensaje",
                    "finalizado_en",
                ]
            )
            _mark_schedule_result(job.scheduled_job, success=False, error=str(exc))
        auditoria.registrar_evento(
            categoria="job",
            accion="error",
            descripcion=f"Error ejecutando job {job.job_type}",
            detalle=str(exc),
            metadata={"job_id": job.pk, "retry": retry, "intentos": job.intentos},
            instancia=job,
        )
        return job

    job.estado = "exitoso"
    job.locked_by = ""
    job.locked_en = None
    job.resultado = result
    job.error_mensaje = ""
    job.finalizado_en = timezone.now()
    job.save(
        update_fields=[
            "estado",
            "locked_by",
            "locked_en",
            "resultado",
            "error_mensaje",
            "finalizado_en",
        ]
    )
    _mark_schedule_result(job.scheduled_job, success=True)
    auditoria.registrar_evento(
        categoria="job",
        accion="ejecutado",
        descripcion=f"Job ejecutado: {job.job_type}",
        metadata={"job_id": job.pk, "resultado": result},
        instancia=job,
    )
    return job


def run_pending_jobs(*, limit: int = 20, worker_name: str = "worker-e1") -> list[models.AsyncJob]:
    processed: list[models.AsyncJob] = []
    for _ in range(max(0, limit)):
        job = run_single_job(worker_name=worker_name)
        if job is None:
            break
        processed.append(job)
    return processed


@register_job_handler("data_quality_scan")
def _run_data_quality_scan(job: models.AsyncJob) -> dict[str, Any]:
    from tramites.services.data_quality import run_quality_scan

    run = run_quality_scan(origen="programado", async_job=job)
    return {"run_id": run.pk, "estado": run.estado, "resumen": run.resumen}


@register_job_handler("healthcheck")
def _run_healthcheck(job: models.AsyncJob) -> dict[str, Any]:
    return {
        "ok": True,
        "job_id": job.pk,
        "executed_at": timezone.now().isoformat(),
    }


@register_job_handler("sla_alert_scan")
def _run_sla_alert_scan(job: models.AsyncJob) -> dict[str, Any]:
    from tramites.services.sla import run_sla_alert_scan

    return run_sla_alert_scan(async_job=job)
