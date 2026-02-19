from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db.models.fields.files import FieldFile

from tramites import logging_utils, models


def _to_primitive(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, FieldFile):
        return value.name or ""
    if isinstance(value, dict):
        return {str(key): _to_primitive(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_primitive(item) for item in value]
    return value


def serialize_instance(instance) -> dict[str, Any]:
    """Serializa campos concretos del modelo para bitácora antes/después."""
    data: dict[str, Any] = {}
    for field in instance._meta.fields:
        key = field.name
        if field.is_relation:
            data[key] = getattr(instance, field.attname, None)
            continue
        data[key] = _to_primitive(getattr(instance, key, None))
    return data


def diff_snapshots(before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    before = before or {}
    after = after or {}
    changes: dict[str, dict[str, Any]] = {}
    for key in sorted(set(before.keys()) | set(after.keys())):
        if before.get(key) == after.get(key):
            continue
        changes[key] = {"antes": before.get(key), "despues": after.get(key)}
    return changes


def _resolve_actor(actor=None, *, fallback_instance=None):
    if getattr(actor, "is_authenticated", False):
        return actor
    ctx_actor = logging_utils.get_request_user_object()
    if getattr(ctx_actor, "is_authenticated", False):
        return ctx_actor
    if fallback_instance is not None:
        for field_name in ("usuario", "creado_por", "actualizado_por"):
            candidate = getattr(fallback_instance, field_name, None)
            if getattr(candidate, "is_authenticated", False):
                return candidate
    return None


def _resolve_content_target(
    *,
    instancia=None,
    content_type=None,
    object_id=None,
):
    if instancia is not None and (content_type is None or object_id is None):
        content_type = ContentType.objects.get_for_model(instancia.__class__)
        object_id = object_id or getattr(instancia, "pk", None)
    return content_type, object_id


def _resolve_related_ids(
    *,
    instancia=None,
    caso_id=None,
    tramite_id=None,
    licencia_id=None,
) -> tuple[int | None, int | None, int | None]:
    if instancia is not None:
        if isinstance(instancia, models.CasoInterno):
            caso_id = caso_id or instancia.pk
        elif isinstance(instancia, models.TramiteCaso):
            tramite_id = tramite_id or instancia.pk
            caso_id = caso_id or instancia.caso_id
        elif isinstance(instancia, models.LicenciaRegistro):
            licencia_id = licencia_id or instancia.pk
        elif isinstance(instancia, models.HistorialEstatusCaso):
            caso_id = caso_id or instancia.caso_id
        elif isinstance(instancia, models.HistorialEstatusTramiteCaso):
            tramite_id = tramite_id or instancia.tramite_id
        elif isinstance(instancia, models.HistorialEstatusLicencia):
            licencia_id = licencia_id or instancia.licencia_id
    return caso_id, tramite_id, licencia_id


def _drop_deleted_self_reference(
    *,
    accion: str,
    instancia=None,
    caso_id: int | None,
    tramite_id: int | None,
    licencia_id: int | None,
) -> tuple[int | None, int | None, int | None]:
    """Evita FK colgantes cuando se audita la eliminación del mismo objeto."""
    if accion != "eliminado" or instancia is None:
        return caso_id, tramite_id, licencia_id
    if isinstance(instancia, models.CasoInterno):
        caso_id = None
    elif isinstance(instancia, models.TramiteCaso):
        tramite_id = None
    elif isinstance(instancia, models.LicenciaRegistro):
        licencia_id = None
    return caso_id, tramite_id, licencia_id


def registrar_evento(
    *,
    categoria: str,
    accion: str,
    descripcion: str,
    detalle: str = "",
    metadata: dict[str, Any] | None = None,
    actor=None,
    instancia=None,
    content_type=None,
    object_id: int | None = None,
    caso_id: int | None = None,
    tramite_id: int | None = None,
    licencia_id: int | None = None,
    request_id: str | None = None,
) -> models.EventoSistema:
    actor = _resolve_actor(actor, fallback_instance=instancia)
    content_type, object_id = _resolve_content_target(
        instancia=instancia,
        content_type=content_type,
        object_id=object_id,
    )
    caso_id, tramite_id, licencia_id = _resolve_related_ids(
        instancia=instancia,
        caso_id=caso_id,
        tramite_id=tramite_id,
        licencia_id=licencia_id,
    )
    caso_id, tramite_id, licencia_id = _drop_deleted_self_reference(
        accion=accion,
        instancia=instancia,
        caso_id=caso_id,
        tramite_id=tramite_id,
        licencia_id=licencia_id,
    )
    req_id = request_id if request_id is not None else logging_utils.get_request_id()
    if req_id == "-":
        req_id = ""
    return models.EventoSistema.objects.create(
        categoria=categoria,
        accion=accion,
        descripcion=descripcion[:255],
        detalle=detalle or "",
        metadata=metadata or {},
        actor=actor,
        request_id=req_id,
        content_type=content_type,
        object_id=object_id,
        caso_id=caso_id,
        tramite_id=tramite_id,
        licencia_id=licencia_id,
    )


def registrar_cambio_critico(
    *,
    modulo: str,
    accion: str,
    descripcion: str,
    antes: dict[str, Any] | None = None,
    despues: dict[str, Any] | None = None,
    cambios: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    actor=None,
    instancia=None,
    content_type=None,
    object_id: int | None = None,
    object_repr: str = "",
    caso_id: int | None = None,
    tramite_id: int | None = None,
    licencia_id: int | None = None,
    request_id: str | None = None,
    emitir_evento: bool = True,
) -> models.BitacoraCambioCritico | None:
    actor = _resolve_actor(actor, fallback_instance=instancia)
    content_type, object_id = _resolve_content_target(
        instancia=instancia,
        content_type=content_type,
        object_id=object_id,
    )
    if content_type is None or object_id is None:
        return None
    caso_id, tramite_id, licencia_id = _resolve_related_ids(
        instancia=instancia,
        caso_id=caso_id,
        tramite_id=tramite_id,
        licencia_id=licencia_id,
    )
    caso_id, tramite_id, licencia_id = _drop_deleted_self_reference(
        accion=accion,
        instancia=instancia,
        caso_id=caso_id,
        tramite_id=tramite_id,
        licencia_id=licencia_id,
    )
    before_data = _to_primitive(antes or {})
    after_data = _to_primitive(despues or {})
    change_data = _to_primitive(cambios or diff_snapshots(before_data, after_data))
    req_id = request_id if request_id is not None else logging_utils.get_request_id()
    if req_id == "-":
        req_id = ""
    bitacora = models.BitacoraCambioCritico.objects.create(
        modulo=modulo,
        accion=accion,
        descripcion=descripcion[:255],
        actor=actor,
        request_id=req_id,
        content_type=content_type,
        object_id=object_id,
        objeto_repr=(object_repr or str(instancia) if instancia is not None else object_repr)[:255],
        antes=before_data,
        despues=after_data,
        cambios=change_data,
        metadata=_to_primitive(metadata or {}),
        caso_id=caso_id,
        tramite_id=tramite_id,
        licencia_id=licencia_id,
    )
    if emitir_evento:
        categoria = modulo if modulo in dict(models.EventoSistema.CATEGORIA_CHOICES) else "sistema"
        registrar_evento(
            categoria=categoria,
            accion=accion if accion in dict(models.EventoSistema.ACCION_CHOICES) else "actualizado",
            descripcion=descripcion,
            metadata={
                "bitacora_id": bitacora.pk,
                "modulo": modulo,
                "cambios": change_data,
                **(metadata or {}),
            },
            actor=actor,
            content_type=content_type,
            object_id=object_id,
            caso_id=caso_id,
            tramite_id=tramite_id,
            licencia_id=licencia_id,
            request_id=req_id,
        )
    return bitacora
