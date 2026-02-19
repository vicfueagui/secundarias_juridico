"""Notificaciones internas para la bandeja de entrada."""
from __future__ import annotations

from typing import Iterable

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from tramites import models


User = get_user_model()


def _truncate_text(value: str, max_chars: int = 220) -> str:
    text = " ".join((value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _usuarios_activos(usuarios: Iterable[User]) -> list[User]:
    return [user for user in usuarios if user and user.is_active]


def _usuarios_caso(caso: models.CasoInterno) -> list[User]:
    return list(caso.usuarios_involucrados.filter(is_active=True))


def _usuarios_tramite(tramite: models.TramiteCaso) -> list[User]:
    usuarios = list(tramite.usuarios_involucrados.filter(is_active=True))
    if usuarios:
        return usuarios
    return _usuarios_caso(tramite.caso)


def _usuarios_union(*grupos: Iterable[User]) -> list[User]:
    usuarios = []
    for grupo in grupos:
        usuarios.extend(grupo)
    vistos = set()
    resultado = []
    for usuario in _usuarios_activos(usuarios):
        if usuario.pk in vistos:
            continue
        vistos.add(usuario.pk)
        resultado.append(usuario)
    return resultado


def _crear_notificacion(
    *,
    evento: str,
    titulo: str,
    mensaje: str,
    usuarios: Iterable[User],
    actor: User | None = None,
    caso: models.CasoInterno | None = None,
    tramite: models.TramiteCaso | None = None,
    referencia: str = "",
) -> models.BandejaNotificacion | None:
    destinatarios = _usuarios_activos(usuarios)
    if not destinatarios:
        return None
    with transaction.atomic():
        notificacion = models.BandejaNotificacion.objects.create(
            evento=evento,
            titulo=titulo,
            mensaje=mensaje,
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            caso=caso,
            tramite=tramite,
            referencia=referencia or "",
        )
        modelos = [
            models.BandejaNotificacionDestinatario(
                notificacion=notificacion,
                usuario=usuario,
            )
            for usuario in destinatarios
        ]
        models.BandejaNotificacionDestinatario.objects.bulk_create(modelos, ignore_conflicts=True)
    return notificacion


def notificar_caso_creado(caso: models.CasoInterno, actor: User | None = None) -> None:
    _crear_notificacion(
        evento="caso_creado",
        titulo=f"Nuevo caso · {caso.cct} · {caso.fecha_apertura}",
        mensaje=f"{caso.descripcion_breve or 'Sin descripción'}",
        usuarios=_usuarios_caso(caso),
        actor=actor,
        caso=caso,
    )


def notificar_caso_actualizado(caso: models.CasoInterno, actor: User | None = None) -> None:
    _crear_notificacion(
        evento="caso_actualizado",
        titulo=f"Caso actualizado · {caso.cct}",
        mensaje=f"Estatus: {caso.estatus or 'Sin estatus'}",
        usuarios=_usuarios_caso(caso),
        actor=actor,
        caso=caso,
    )


def notificar_caso_mencion(
    *,
    comentario: models.CasoComentarioInterno,
    usuarios: Iterable[User] | None = None,
    actor: User | None = None,
) -> None:
    destinatarios = list(usuarios) if usuarios is not None else list(comentario.menciones.filter(is_active=True))
    if actor and getattr(actor, "is_authenticated", False):
        destinatarios = [user for user in destinatarios if user.pk != actor.pk]
    if not destinatarios:
        return
    resumen = _truncate_text(comentario.mensaje or "")
    _crear_notificacion(
        evento="caso_mencion",
        titulo=f"Mención en expediente · Caso {comentario.caso_id}",
        mensaje=resumen or "Te mencionaron en un comentario interno.",
        usuarios=destinatarios,
        actor=actor,
        caso=comentario.caso,
        referencia=f"Comentario #{comentario.pk}",
    )


def notificar_caso_tarea_asignada(
    tarea: models.CasoTareaInterna,
    *,
    actor: User | None = None,
) -> None:
    responsable = tarea.responsable
    if not responsable or not responsable.is_active:
        return
    if actor and getattr(actor, "is_authenticated", False) and responsable.pk == actor.pk:
        return
    _crear_notificacion(
        evento="caso_tarea_asignada",
        titulo=f"Tarea interna asignada · Caso {tarea.caso_id}",
        mensaje=f"{tarea.titulo} · Compromiso {tarea.fecha_compromiso:%d/%m/%Y}",
        usuarios=[responsable],
        actor=actor,
        caso=tarea.caso,
        referencia=f"Tarea #{tarea.pk}",
    )


def notificar_caso_tarea_completada(
    tarea: models.CasoTareaInterna,
    *,
    actor: User | None = None,
) -> None:
    grupos = []
    if tarea.creada_por and tarea.creada_por.is_active:
        grupos.append([tarea.creada_por])
    if tarea.responsable and tarea.responsable.is_active:
        grupos.append([tarea.responsable])
    destinatarios = _usuarios_union(*grupos) if grupos else []
    if actor and getattr(actor, "is_authenticated", False):
        destinatarios = [user for user in destinatarios if user.pk != actor.pk]
    if not destinatarios:
        return
    completada_en = tarea.completada_en or timezone.now()
    _crear_notificacion(
        evento="caso_tarea_completada",
        titulo=f"Tarea interna completada · Caso {tarea.caso_id}",
        mensaje=f"{tarea.titulo} · Completada {completada_en:%d/%m/%Y %H:%M}",
        usuarios=destinatarios,
        actor=actor,
        caso=tarea.caso,
        referencia=f"Tarea #{tarea.pk}",
    )


def notificar_caso_estatus(
    caso: models.CasoInterno,
    estatus_anterior: models.EstatusCaso | None,
    estatus_nuevo: models.EstatusCaso | None,
    comentario: str = "",
    actor: User | None = None,
) -> None:
    _crear_notificacion(
        evento="caso_estatus",
        titulo=f"Estatus de caso actualizado · {caso.cct}",
        mensaje=(
            f"{estatus_anterior or 'Sin estatus'} → {estatus_nuevo or 'Sin estatus'}"
            f"{' · ' + comentario if comentario else ''}"
        ),
        usuarios=_usuarios_caso(caso),
        actor=actor,
        caso=caso,
    )


def notificar_caso_eliminado(caso: models.CasoInterno, actor: User | None = None) -> None:
    referencia = f"{caso.cct} · {caso.descripcion_breve or 'Sin descripción'}"
    _crear_notificacion(
        evento="caso_eliminado",
        titulo="Caso eliminado",
        mensaje=referencia,
        usuarios=_usuarios_caso(caso),
        actor=actor,
        referencia=referencia,
    )


def notificar_tramite_creado(tramite: models.TramiteCaso, actor: User | None = None) -> None:
    _crear_notificacion(
        evento="tramite_creado",
        titulo=f"Trámite asociado creado · Caso {tramite.caso_id}",
        mensaje=f"{tramite.tipo} · {tramite.fecha}",
        usuarios=_usuarios_tramite(tramite),
        actor=actor,
        caso=tramite.caso,
        tramite=tramite,
    )


def notificar_tramite_actualizado(tramite: models.TramiteCaso, actor: User | None = None) -> None:
    _crear_notificacion(
        evento="tramite_actualizado",
        titulo=f"Trámite asociado actualizado · Caso {tramite.caso_id}",
        mensaje=f"{tramite.tipo} · Estatus: {tramite.estatus or 'Sin estatus'}",
        usuarios=_usuarios_tramite(tramite),
        actor=actor,
        caso=tramite.caso,
        tramite=tramite,
    )


def notificar_tramite_estatus(
    tramite: models.TramiteCaso,
    estatus_anterior: models.EstatusTramite | None,
    estatus_nuevo: models.EstatusTramite | None,
    comentario: str = "",
    actor: User | None = None,
) -> None:
    _crear_notificacion(
        evento="tramite_estatus",
        titulo=f"Estatus de trámite actualizado · Caso {tramite.caso_id}",
        mensaje=(
            f"{estatus_anterior or 'Sin estatus'} → {estatus_nuevo or 'Sin estatus'}"
            f"{' · ' + comentario if comentario else ''}"
        ),
        usuarios=_usuarios_tramite(tramite),
        actor=actor,
        caso=tramite.caso,
        tramite=tramite,
    )


def notificar_tramite_eliminado(tramite: models.TramiteCaso, actor: User | None = None) -> None:
    referencia = f"{tramite.tipo} · {tramite.fecha}"
    _crear_notificacion(
        evento="tramite_eliminado",
        titulo=f"Trámite asociado eliminado · Caso {tramite.caso_id}",
        mensaje=referencia,
        usuarios=_usuarios_tramite(tramite),
        actor=actor,
        referencia=referencia,
    )


def notificar_sla_alerta(
    *,
    titulo: str,
    mensaje: str,
    usuarios: Iterable[User],
    actor: User | None = None,
    caso: models.CasoInterno | None = None,
    tramite: models.TramiteCaso | None = None,
    referencia: str = "",
) -> None:
    if not (caso or tramite):
        return
    target_case = caso if caso is not None else tramite.caso
    _crear_notificacion(
        evento="sla_alerta",
        titulo=titulo,
        mensaje=mensaje,
        usuarios=usuarios,
        actor=actor,
        caso=target_case,
        tramite=tramite,
        referencia=referencia,
    )


def notificar_sla_escalamiento(
    *,
    titulo: str,
    mensaje: str,
    usuarios: Iterable[User],
    actor: User | None = None,
    caso: models.CasoInterno | None = None,
    tramite: models.TramiteCaso | None = None,
    referencia: str = "",
) -> None:
    if not (caso or tramite):
        return
    target_case = caso if caso is not None else tramite.caso
    _crear_notificacion(
        evento="sla_escalamiento",
        titulo=titulo,
        mensaje=mensaje,
        usuarios=usuarios,
        actor=actor,
        caso=target_case,
        tramite=tramite,
        referencia=referencia,
    )


def notificar_caso_convertido_a_anexo(
    *,
    caso_origen: models.CasoInterno,
    caso_destino: models.CasoInterno,
    tramite: models.TramiteCaso,
    actor: User | None = None,
    motivo: str = "",
) -> None:
    usuarios = _usuarios_union(_usuarios_caso(caso_origen), _usuarios_caso(caso_destino))
    motivo_txt = f" · Motivo: {motivo}" if motivo else ""
    _crear_notificacion(
        evento="caso_convertido_anexo",
        titulo=f"Caso convertido en trámite anexo · Caso {caso_destino.pk}",
        mensaje=f"Origen: {caso_origen.numero_oficio or caso_origen.pk} · Anexo: {tramite.tipo}{motivo_txt}",
        usuarios=usuarios,
        actor=actor,
        caso=caso_destino,
        tramite=tramite,
        referencia=f"Origen {caso_origen.pk} → Destino {caso_destino.pk}",
    )

def notificar_minuta_eliminada_caso(
    caso: models.CasoInterno,
    *,
    actor: User | None = None,
    referencia: str = "",
) -> None:
    _crear_notificacion(
        evento="minuta_eliminada",
        titulo=f"Minuta eliminada · {caso.cct}",
        mensaje=referencia or (caso.descripcion_breve or "Minuta eliminada."),
        usuarios=_usuarios_caso(caso),
        actor=actor,
        caso=caso,
        referencia=referencia,
    )


def notificar_minuta_eliminada_tramite(
    tramite: models.TramiteCaso,
    *,
    actor: User | None = None,
    referencia: str = "",
) -> None:
    _crear_notificacion(
        evento="minuta_eliminada",
        titulo=f"Minuta eliminada · Caso {tramite.caso_id}",
        mensaje=referencia or f"{tramite.tipo} · {tramite.fecha}",
        usuarios=_usuarios_tramite(tramite),
        actor=actor,
        caso=tramite.caso,
        tramite=tramite,
        referencia=referencia,
    )


def marcar_notificaciones_leidas(
    *,
    usuario: User,
    caso: models.CasoInterno | None = None,
    tramite: models.TramiteCaso | None = None,
) -> int:
    qs = models.BandejaNotificacionDestinatario.objects.filter(usuario=usuario, leido=False)
    if caso is not None:
        qs = qs.filter(notificacion__caso=caso)
    if tramite is not None:
        qs = qs.filter(notificacion__tramite=tramite)
    return qs.update(leido=True, leido_en=timezone.now())


def notificar_registro_leido(
    *,
    actor: User,
    caso: models.CasoInterno | None = None,
    tramite: models.TramiteCaso | None = None,
) -> None:
    if not actor or not getattr(actor, "is_authenticated", False):
        return
    if tramite:
        usuarios = [user for user in _usuarios_tramite(tramite) if user != actor]
        referencia = f"{tramite.tipo} · Caso {tramite.caso_id}"
    else:
        usuarios = [user for user in _usuarios_caso(caso) if user != actor]
        referencia = f"{caso.cct} · {caso.descripcion_breve or 'Sin descripción'}"
    if not usuarios:
        return
    _crear_notificacion(
        evento="registro_leido",
        titulo="Registro leído",
        mensaje=f"{actor.get_full_name() or actor.username} leyó {referencia}.",
        usuarios=usuarios,
        actor=actor,
        caso=caso if caso else tramite.caso,
        tramite=tramite,
        referencia=referencia,
    )
