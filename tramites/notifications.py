"""Notificaciones por correo para cambios relevantes en los trámites."""
from __future__ import annotations

import logging
from typing import Iterable

from django.conf import settings
from django.core.mail import send_mail

from tramites import models

logger = logging.getLogger(__name__)


def _clean_recipients(emails: Iterable[str]) -> list[str]:
    cleaned = []
    seen = set()
    for email in emails:
        value = (email or "").strip()
        if not value or value in seen:
            continue
        cleaned.append(value)
        seen.add(value)
    return cleaned


def _send_notification(subject: str, message: str, recipients: Iterable[str]) -> int:
    emails = _clean_recipients(recipients)
    if not emails:
        logger.info("Notificación omitida: no hay correos destinatarios.")
        return 0
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
    return send_mail(subject, message, from_email, emails, fail_silently=False)


def _emails_caso(caso: models.CasoInterno) -> list[str]:
    return list(
        caso.usuarios_involucrados.filter(is_active=True)
        .exclude(email__isnull=True)
        .exclude(email__exact="")
        .values_list("email", flat=True)
    )


def notificar_caso_creado(caso: models.CasoInterno) -> None:
    subject = f"Nuevo caso registrado · {caso.cct} · {caso.fecha_apertura}"
    message = "\n".join(
        [
            "Se registró un nuevo caso.",
            f"CCT: {caso.cct}",
            f"Fecha: {caso.fecha_apertura}",
            f"Estatus: {caso.estatus or 'Sin estatus'}",
            f"Tipo inicial: {caso.tipo_inicial}",
            f"Descripción: {caso.descripcion_breve or 'Sin descripción'}",
        ]
    )
    _send_notification(subject, message, _emails_caso(caso))


def notificar_tramite_caso_creado(tramite: models.TramiteCaso) -> None:
    subject = f"Nuevo trámite asociado · Caso {tramite.caso_id}"
    message = "\n".join(
        [
            "Se agregó un nuevo trámite a un caso.",
            f"Caso: {tramite.caso}",
            f"Tipo: {tramite.tipo}",
            f"Fecha: {tramite.fecha}",
            f"Estatus: {tramite.estatus or 'Sin estatus'}",
            f"Asunto: {tramite.asunto or 'Sin asunto'}",
        ]
    )
    _send_notification(subject, message, _emails_caso(tramite.caso))


def notificar_estatus_caso(
    caso: models.CasoInterno,
    estatus_anterior: models.EstatusCaso | None,
    estatus_nuevo: models.EstatusCaso | None,
    comentario: str = "",
) -> None:
    subject = f"Estatus actualizado · Caso {caso.id}"
    message = "\n".join(
        [
            "Se actualizó el estatus del caso.",
            f"Caso: {caso}",
            f"Estatus anterior: {estatus_anterior or 'Sin estatus'}",
            f"Estatus nuevo: {estatus_nuevo or 'Sin estatus'}",
            f"Comentario: {comentario or 'Sin comentario'}",
        ]
    )
    _send_notification(subject, message, _emails_caso(caso))


def notificar_estatus_tramite(
    tramite: models.TramiteCaso,
    estatus_anterior: models.EstatusTramite | None,
    estatus_nuevo: models.EstatusTramite | None,
    comentario: str = "",
) -> None:
    subject = f"Estatus actualizado · Trámite del caso {tramite.caso_id}"
    message = "\n".join(
        [
            "Se actualizó el estatus de un trámite asociado.",
            f"Caso: {tramite.caso}",
            f"Trámite: {tramite}",
            f"Estatus anterior: {estatus_anterior or 'Sin estatus'}",
            f"Estatus nuevo: {estatus_nuevo or 'Sin estatus'}",
            f"Comentario: {comentario or 'Sin comentario'}",
        ]
    )
    _send_notification(subject, message, _emails_caso(tramite.caso))
