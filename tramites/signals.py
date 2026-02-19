"""Señales para mantener estatus sincronizados con el historial."""
from __future__ import annotations

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from tramites import models
from tramites.services import auditoria


AUDITED_MODELS = {
    models.CasoInterno: "caso",
    models.TramiteCaso: "tramite",
    models.LicenciaRegistro: "licencia",
    models.FeatureFlag: "feature_flag",
    models.FeatureFlagGrupo: "feature_flag",
    models.ScheduledJob: "job",
    models.SLARegla: "sistema",
}

AUDIT_IGNORED_FIELDS = {
    "creado_en",
    "actualizado_en",
    "fecha_registro",
    "fecha_cambio",
    "locked_en",
    "iniciado_en",
    "finalizado_en",
    "primer_detectado_en",
    "ultimo_detectado_en",
}


def _snapshot_for_audit(instance) -> dict:
    raw = auditoria.serialize_instance(instance)
    return {key: value for key, value in raw.items() if key not in AUDIT_IGNORED_FIELDS}


def _resolve_action(sender, *, created: bool, changes: dict) -> str:
    if created:
        return "creado"
    if sender in {models.FeatureFlag, models.FeatureFlagGrupo} and "habilitado" in changes:
        return "habilitado" if changes["habilitado"]["despues"] else "deshabilitado"
    return "actualizado"


def _resolve_description(sender, action: str) -> str:
    label = sender._meta.verbose_name.title()
    action_label = {
        "creado": "creado",
        "actualizado": "actualizado",
        "eliminado": "eliminado",
        "habilitado": "habilitado",
        "deshabilitado": "deshabilitado",
    }.get(action, action)
    return f"{label} {action_label}"


@receiver(pre_save)
def _capture_previous_snapshot(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    if not getattr(instance, "pk", None):
        instance._audit_before = {}
        return
    previous = sender.objects.filter(pk=instance.pk).first()
    instance._audit_before = _snapshot_for_audit(previous) if previous else {}


@receiver(post_save)
def _audit_critical_changes_on_save(sender, instance, created, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    before = getattr(instance, "_audit_before", {}) or {}
    after = _snapshot_for_audit(instance)
    changes = auditoria.diff_snapshots(before, after)
    if not created and not changes:
        return
    action = _resolve_action(sender, created=created, changes=changes)
    actor = None
    for field_name in ("usuario", "creado_por", "actualizado_por"):
        candidate = getattr(instance, field_name, None)
        if getattr(candidate, "is_authenticated", False):
            actor = candidate
            break
    auditoria.registrar_cambio_critico(
        modulo=AUDITED_MODELS[sender],
        accion=action if action in dict(models.BitacoraCambioCritico.ACCION_CHOICES) else "actualizado",
        descripcion=_resolve_description(sender, action),
        antes=before,
        despues=after,
        cambios=changes,
        actor=actor,
        instancia=instance,
    )


@receiver(post_delete)
def _audit_critical_changes_on_delete(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    before = _snapshot_for_audit(instance)
    actor = None
    for field_name in ("usuario", "creado_por", "actualizado_por"):
        candidate = getattr(instance, field_name, None)
        if getattr(candidate, "is_authenticated", False):
            actor = candidate
            break
    auditoria.registrar_cambio_critico(
        modulo=AUDITED_MODELS[sender],
        accion="eliminado",
        descripcion=_resolve_description(sender, "eliminado"),
        antes=before,
        despues={},
        cambios=auditoria.diff_snapshots(before, {}),
        actor=actor,
        instancia=instance,
    )


def _actualizar_estatus_tramite(tramite_id: int | None) -> None:
    if not tramite_id:
        return
    ultimo = (
        models.HistorialEstatusTramiteCaso.objects.filter(tramite_id=tramite_id)
        .order_by("-fecha_cambio", "-id")
        .first()
    )
    models.TramiteCaso.objects.filter(pk=tramite_id).update(
        estatus=ultimo.estatus_nuevo if ultimo else None,
        actualizado_en=timezone.now(),
    )


def _actualizar_estatus_caso(caso_id: int | None) -> None:
    if not caso_id:
        return
    ultimo = (
        models.HistorialEstatusCaso.objects.filter(caso_id=caso_id)
        .order_by("-fecha_cambio", "-id")
        .first()
    )
    if not ultimo:
        return
    models.CasoInterno.objects.filter(pk=caso_id).update(
        estatus=ultimo.estatus_nuevo,
        actualizado_en=timezone.now(),
    )


@receiver(post_save, sender=models.HistorialEstatusTramiteCaso)
def _sync_tramite_estatus_on_save(sender, instance, **kwargs) -> None:
    _actualizar_estatus_tramite(instance.tramite_id)


@receiver(post_delete, sender=models.HistorialEstatusTramiteCaso)
def _sync_tramite_estatus_on_delete(sender, instance, **kwargs) -> None:
    _actualizar_estatus_tramite(instance.tramite_id)


@receiver(post_save, sender=models.HistorialEstatusCaso)
def _sync_caso_estatus_on_save(sender, instance, **kwargs) -> None:
    _actualizar_estatus_caso(instance.caso_id)


@receiver(post_delete, sender=models.HistorialEstatusCaso)
def _sync_caso_estatus_on_delete(sender, instance, **kwargs) -> None:
    _actualizar_estatus_caso(instance.caso_id)
