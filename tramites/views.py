"""Vistas HTML y API para el módulo de trámites jurídicos."""
from __future__ import annotations

import csv
import json
import logging
import urllib.parse
from types import SimpleNamespace
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import DatabaseError, IntegrityError, models as dj_models, transaction
from django.core.files.base import ContentFile
from django.db.models import Case, Count, IntegerField, Max, Prefetch, Q, Value, When
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html, format_html_join
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.edit import FormView
from django.core.paginator import Paginator
from django_filters.views import FilterView
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from tramites import filters, forms, models, serializers
from tramites import inbox, notifications
from tramites.services import auditoria, captura_guiada, data_quality, feature_flags, jobs, operacion, sla
from tramites.services.plantillas_cache import (
    clear_empleado_cache,
    get_latest_registro_info,
)
from tramites.utils import normalise_sistema

logger = logging.getLogger(__name__)


_CCT_CATALOG_LOADED = False
FOLIO_PREFIJO_DEFAULT = "SE/SEB/DES-EESP"
FOLIO_PREFIJO_INICIO_2026 = 184


DEFAULT_USUARIOS_INVOLUCRADOS = [
    "maria.garciago",
    "admin",
    "dulce.luna",
    "claudio.diaz",
    "jaime.pacheco",
    "neggie.rubio",
]

ASESOR_USUARIO_MAP = {
    "ANGEL": "angel.canche",
    "ALICIA": "alicia.alcerreca",
    "CARLOS": "carlos.vales",
    "CINDY": "cindy.baeza",
    "SANDY": "sandy.garcia",
}

FILTROS_GUARDADOS_KEYS_CASOS = {
    "buscar",
    "cct",
    "estatus",
    "tipo_inicial",
    "creado_por",
    "asesor_cct",
    "tipo_violencia",
    "trabajador",
    "generador_iniciales",
    "receptor_iniciales",
    "fecha_apertura_after",
    "fecha_apertura_before",
    "fecha_registro_after",
    "fecha_registro_before",
    "metric",
    "year",
    "modalidad",
    "violencia",
    "generador_sexo",
    "receptor_sexo",
    "asesor",
    "tramite_tipo",
    "tramite_estatus",
    "orden",
    "show_ids",
}
FILTROS_GUARDADOS_KEYS_COLA = {
    "tipo",
    "prioridad",
    "estado",
}


def _sanitize_saved_filter_pairs(
    raw_pairs: list[tuple[str, str]],
    *,
    allowed_keys: set[str],
) -> str:
    cleaned: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw_key, raw_value in raw_pairs:
        key = (raw_key or "").strip()
        value = (raw_value or "").strip()
        if key not in allowed_keys or not value:
            continue
        if len(value) > 220:
            continue
        pair = (key, value)
        if pair in seen:
            continue
        seen.add(pair)
        cleaned.append(pair)
        if len(cleaned) >= 40:
            break
    return urllib.parse.urlencode(cleaned, doseq=True)


def _sanitize_saved_filter_querystring(raw_querystring: str, *, allowed_keys: set[str]) -> str:
    pairs = urllib.parse.parse_qsl(raw_querystring or "", keep_blank_values=False)
    return _sanitize_saved_filter_pairs(pairs, allowed_keys=allowed_keys)


def _build_saved_filter_querystring_from_request(request: HttpRequest, *, allowed_keys: set[str]) -> str:
    pairs: list[tuple[str, str]] = []
    for key, values in request.GET.lists():
        if key in {"page", "anexos_page"}:
            continue
        for value in values:
            pairs.append((key, value))
    return _sanitize_saved_filter_pairs(pairs, allowed_keys=allowed_keys)


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_form_choice_id(form, field_name: str) -> int | None:
    if not form or field_name not in getattr(form, "fields", {}):
        return None
    if form.is_bound:
        raw = form.data.get(form.add_prefix(field_name))
        if raw in (None, ""):
            raw = form.data.get(field_name)
        return _safe_int(raw)
    initial = form.initial.get(field_name)
    if initial in (None, "") and getattr(form, "instance", None) is not None:
        initial = getattr(form.instance, f"{field_name}_id", None)
    if hasattr(initial, "pk"):
        return getattr(initial, "pk", None)
    return _safe_int(initial)


def _build_captura_guiada_context(form, *, ambito: str) -> dict[str, Any]:
    if ambito == captura_guiada.AMBITO_TRAMITE:
        tipo_field = "tipo"
    else:
        tipo_field = "tipo_inicial"
    estatus_field = "estatus"
    tipo_qs = form.fields[tipo_field].queryset if tipo_field in form.fields else models.TipoProceso.objects.none()
    estatus_qs = (
        form.fields[estatus_field].queryset
        if estatus_field in form.fields
        else models.EstatusCaso.objects.none()
    )
    checklist = {}
    if getattr(form, "instance", None) is not None:
        checklist = getattr(form.instance, "checklist_documental", {}) or {}
    return captura_guiada.build_frontend_config(
        ambito=ambito,
        tipo_queryset=tipo_qs,
        estatus_queryset=estatus_qs,
        selected_tipo_id=_extract_form_choice_id(form, tipo_field),
        selected_estatus_id=_extract_form_choice_id(form, estatus_field),
        checklist_documental=checklist,
    )


def _operacion_assignable_users():
    return list(
        get_user_model()
        .objects.filter(is_active=True)
        .order_by("username")
        .values("id", "username")
    )


def _resolve_next_url(request: HttpRequest, *, fallback: str) -> str:
    next_url = (request.POST.get("next") or "").strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return fallback


def _resolver_usuarios_por_usernames(usernames: list[str]):
    User = get_user_model()
    usuarios = list(User.objects.filter(username__in=usernames))
    return usuarios


def _usuarios_involucrados_default(caso: models.CasoInterno) -> list:
    usernames = list(DEFAULT_USUARIOS_INVOLUCRADOS)
    asesor_key = (caso.asesor_cct or "").strip().upper()
    asesor_username = ASESOR_USUARIO_MAP.get(asesor_key)
    if asesor_username:
        usernames.append(asesor_username)
    return _resolver_usuarios_por_usernames(usernames)


def ensure_cct_catalog_loaded() -> None:
    """Verifica una sola vez si existen CCT cargados."""
    global _CCT_CATALOG_LOADED
    if _CCT_CATALOG_LOADED:
        return
    try:
        if models.PlantillaCentroTrabajo.objects.exists():
            _CCT_CATALOG_LOADED = True
        else:
            logger.warning(
                "Catálogo de CCT vacío. Ejecuta `python manage.py import_plantillas --path cct_secundarias.csv`."
            )
            _CCT_CATALOG_LOADED = True
    except DatabaseError:
        logger.warning("No se pudo verificar el catálogo de CCT (base de datos no disponible).")


def _get_folio_consecutivo(anio: int, prefijo: str, usuario) -> models.FolioConsecutivo:
    if anio == 2026 and prefijo == FOLIO_PREFIJO_DEFAULT:
        ultimo_numero = FOLIO_PREFIJO_INICIO_2026
    else:
        ultimo_numero = 0
    defaults = {"ultimo_numero": ultimo_numero, "actualizado_por": usuario}
    consecutivo, _ = models.FolioConsecutivo.objects.get_or_create(
        anio=anio,
        prefijo=prefijo,
        defaults=defaults,
    )
    return consecutivo


def _generar_folio(
    *,
    usuario,
    tipo: str,
    caso: models.CasoInterno | None = None,
    casos: list[models.CasoInterno] | tuple[models.CasoInterno, ...] | None = None,
    tramite: models.TramiteCaso | None = None,
    prefijo: str = FOLIO_PREFIJO_DEFAULT,
) -> models.FolioRegistro:
    anio = timezone.localdate().year
    if casos is None and caso is not None:
        casos = [caso]
    with transaction.atomic():
        consecutivo = models.FolioConsecutivo.objects.select_for_update().filter(
            anio=anio, prefijo=prefijo
        ).first()
        if not consecutivo:
            consecutivo = _get_folio_consecutivo(anio, prefijo, usuario)
        if (
            anio == 2026
            and prefijo == FOLIO_PREFIJO_DEFAULT
            and consecutivo.ultimo_numero < FOLIO_PREFIJO_INICIO_2026
        ):
            consecutivo.ultimo_numero = FOLIO_PREFIJO_INICIO_2026
        consecutivo.ultimo_numero += 1
        consecutivo.actualizado_por = usuario
        consecutivo.save(update_fields=["ultimo_numero", "actualizado_en", "actualizado_por"])
        folio_texto = f"{prefijo}/{consecutivo.ultimo_numero}/{anio}"
        registro = models.FolioRegistro.objects.create(
            anio=anio,
            prefijo=prefijo,
            numero=consecutivo.ultimo_numero,
            folio=folio_texto,
            tipo=tipo,
            tramite=tramite,
            creado_por=usuario if getattr(usuario, "is_authenticated", False) else None,
        )
        if casos:
            registro.casos.add(*casos)
        models.FolioActividad.objects.create(
            folio=registro,
            accion="creado",
            usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
            detalle="Generación automática de folio",
        )
        return registro


def _get_folio_generado_id(request: HttpRequest, prefix: str | None = None) -> str:
    if prefix:
        value = (request.POST.get(f"{prefix}-folio_generado_id") or "").strip()
        if value:
            return value
    return (request.POST.get("folio_generado_id") or "").strip()


def _parse_folio_ids(values: list[str] | tuple[str, ...] | str | None) -> list[int]:
    if values is None:
        return []
    if isinstance(values, str):
        raw_values = [values]
    else:
        raw_values = list(values)
    folio_ids: list[int] = []
    for raw in raw_values:
        for token in str(raw or "").replace(";", ",").split(","):
            value = token.strip()
            if not value:
                continue
            try:
                folio_ids.append(int(value))
            except (TypeError, ValueError):
                continue
    # Mantener orden de llegada, sin duplicados.
    return list(dict.fromkeys(folio_ids))


def _get_folios_preview_ids(request: HttpRequest, prefix: str | None = None) -> list[int]:
    values: list[str] = []
    if prefix:
        prefixed = (request.POST.get(f"{prefix}-folio_generado_id") or "").strip()
        if prefixed:
            values.append(prefixed)
    for key in ("folio_generado_id", "folio_id", "folio_ids", "folio_ids[]"):
        values.extend(request.POST.getlist(key))
    return _parse_folio_ids(values)


def _cancelar_folios_preview(
    *,
    folio_ids: list[int],
    usuario,
    detalle: str = "",
) -> int:
    ids = [folio_id for folio_id in dict.fromkeys(folio_ids) if folio_id]
    if not ids:
        return 0
    actor = usuario if getattr(usuario, "is_authenticated", False) else None
    with transaction.atomic():
        through_model = models.FolioRegistro.casos.through
        ids_con_caso = set(
            through_model.objects.filter(folioregistro_id__in=ids).values_list(
                "folioregistro_id",
                flat=True,
            )
        )
        ids_elegibles = [folio_id for folio_id in ids if folio_id not in ids_con_caso]
        if not ids_elegibles:
            return 0
        folios_qs = models.FolioRegistro.objects.select_for_update().filter(
            pk__in=ids_elegibles,
            activo=True,
            tramite__isnull=True,
        )
        if actor:
            folios_qs = folios_qs.filter(creado_por=actor)
        folios = list(folios_qs)
        if not folios:
            return 0
        now = timezone.now()
        detalle_final = detalle or "Folio provisional cancelado automáticamente por formulario no guardado."
        cancelados = 0
        for folio in folios:
            # Revalida contra la relación M2M por posibles cambios concurrentes.
            if folio.casos.exists():
                continue
            folio.activo = False
            folio.eliminado_en = now
            folio.eliminado_por = actor
            folio.notas = (folio.notas or "").strip()
            if detalle_final not in folio.notas:
                folio.notas = f"{folio.notas}\n{detalle_final}".strip() if folio.notas else detalle_final
            folio.save(update_fields=["activo", "eliminado_en", "eliminado_por", "notas"])
            models.FolioActividad.objects.create(
                folio=folio,
                accion="eliminado",
                usuario=actor,
                detalle=detalle_final,
            )
            cancelados += 1
        return cancelados


def _asignar_folio_generado(
    *,
    folio_id: str | int | None,
    caso: models.CasoInterno | None = None,
    tramite: models.TramiteCaso | None = None,
) -> None:
    if not folio_id:
        return
    try:
        folio_pk = int(folio_id)
    except (TypeError, ValueError):
        return
    folio = models.FolioRegistro.objects.filter(pk=folio_pk, activo=True).first()
    if not folio:
        return
    # Evita tomar folios ya asociados a otros registros.
    if folio.tramite_id and (not tramite or folio.tramite_id != tramite.pk):
        return
    if folio.casos.exists() and (not caso or not folio.casos.filter(pk=caso.pk).exists()):
        return
    if caso:
        if folio.tramite_id:
            folio.tramite = None
        folio.tipo = "caso"
        folio.save(update_fields=["tramite", "tipo"])
        folio.casos.add(caso)
        if caso.numero_oficio != folio.folio:
            caso.numero_oficio = folio.folio
            caso.save(update_fields=["numero_oficio", "actualizado_en"])
    if tramite:
        folio.tramite = tramite
        folio.tipo = "tramite"
        folio.save(update_fields=["tramite", "tipo"])
        folio.casos.clear()
        if tramite.numero_oficio != folio.folio:
            tramite.numero_oficio = folio.folio
            tramite.save(update_fields=["numero_oficio", "actualizado_en"])


def _sync_consecutivo_from_folio(folio: models.FolioRegistro, usuario) -> None:
    with transaction.atomic():
        consecutivo = models.FolioConsecutivo.objects.select_for_update().filter(
            anio=folio.anio, prefijo=folio.prefijo
        ).first()
        if not consecutivo:
            consecutivo = models.FolioConsecutivo(
                anio=folio.anio,
                prefijo=folio.prefijo,
                ultimo_numero=0,
            )
        if folio.numero > consecutivo.ultimo_numero:
            consecutivo.ultimo_numero = folio.numero
            consecutivo.actualizado_por = usuario
            consecutivo.save()


def _buscar_duplicados_expediente(
    numero_oficio: str,
    *,
    exclude_caso_id: int | None = None,
    exclude_tramite_id: int | None = None,
) -> tuple[list[models.CasoInterno], list[models.TramiteCaso]]:
    if not numero_oficio:
        return [], []
    normalized = numero_oficio.strip().upper()
    normalized = normalized.replace(".", "").replace("-", "").replace(" ", "")
    if normalized in {"SN", "S/N"}:
        return [], []
    casos = models.CasoInterno.objects.filter(numero_oficio__iexact=numero_oficio)
    tramites = models.TramiteCaso.objects.filter(numero_oficio__iexact=numero_oficio)
    if exclude_caso_id:
        casos = casos.exclude(pk=exclude_caso_id)
    if exclude_tramite_id:
        tramites = tramites.exclude(pk=exclude_tramite_id)
    return list(casos), list(tramites)


def _buscar_coincidencias_participantes(
    *,
    generador_nombre: str = "",
    generador_iniciales: str = "",
    receptor_nombre: str = "",
    receptor_iniciales: str = "",
    exclude_caso_id: int | None = None,
    exclude_tramite_id: int | None = None,
) -> tuple[list[models.CasoInterno], list[models.TramiteCaso]]:
    query = Q()
    if generador_nombre:
        query |= Q(generador_nombre__icontains=generador_nombre)
    if generador_iniciales:
        query |= Q(generador_iniciales__icontains=generador_iniciales)
    if receptor_nombre:
        query |= Q(receptor_nombre__icontains=receptor_nombre)
    if receptor_iniciales:
        query |= Q(receptor_iniciales__icontains=receptor_iniciales)
    if not query:
        return [], []
    casos = models.CasoInterno.objects.filter(query)
    tramites = models.TramiteCaso.objects.filter(query)
    if exclude_caso_id:
        casos = casos.exclude(pk=exclude_caso_id)
    if exclude_tramite_id:
        tramites = tramites.exclude(pk=exclude_tramite_id)
    return list(casos), list(tramites)


def _render_referencias_casos_tramites(
    casos: list[models.CasoInterno],
    tramites: list[models.TramiteCaso],
) -> str:
    rows: list[tuple[str, str]] = []
    for caso in casos:
        url = reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk})
        label = f"Caso #{caso.pk} · {caso.cct_id} · {caso.numero_oficio or 'sin expediente'}"
        rows.append((url, label))
    for tramite in tramites:
        url = reverse(
            "tramites:tramite-caso-detail",
            kwargs={"caso_pk": tramite.caso_id, "pk": tramite.pk},
        )
        label = f"Trámite #{tramite.pk} · Caso {tramite.caso_id} · {tramite.numero_oficio or 'sin expediente'}"
        rows.append((url, label))
    if not rows:
        return ""
    return format_html(
        "<ul class=\"message-list\">{}</ul>",
        format_html_join("", "<li><a href=\"{}\">{}</a></li>", rows),
    )


def _emitir_alerta_duplicados(
    request: HttpRequest,
    *,
    titulo: str,
    casos: list[models.CasoInterno],
    tramites: list[models.TramiteCaso],
) -> None:
    if not casos and not tramites:
        return
    lista = _render_referencias_casos_tramites(casos, tramites)
    messages.warning(
        request,
        format_html("{}{}", titulo, lista),
    )


def _prefetch_tramite_creador(qs):
    return qs.prefetch_related(
        Prefetch(
            "historial_estatus",
            queryset=models.HistorialEstatusTramiteCaso.objects.select_related("usuario").order_by(
                "fecha_cambio",
                "id",
            ),
            to_attr="historial_estatus_creacion",
        )
    )


def _preview_documentos_caso(caso: models.CasoInterno) -> list[dict[str, str]]:
    documentos: list[dict[str, str]] = []
    if caso.minuta:
        documentos.append(
            {
                "nombre": "Documento principal del caso",
                "url": caso.minuta.url,
            }
        )
    for idx, minuta in enumerate(caso.minutas_adjuntas.all(), start=1):
        if minuta.archivo:
            documentos.append(
                {
                    "nombre": f"Minuta adjunta {idx}",
                    "url": minuta.archivo.url,
                }
            )
    return documentos


def _preview_documentos_tramite(tramite: models.TramiteCaso) -> list[dict[str, str]]:
    documentos: list[dict[str, str]] = []
    if tramite.minuta:
        documentos.append(
            {
                "nombre": "Documento principal del tramite anexo",
                "url": tramite.minuta.url,
            }
        )
    for idx, minuta in enumerate(tramite.minutas_adjuntas.all(), start=1):
        if minuta.archivo:
            documentos.append(
                {
                    "nombre": f"Minuta adjunta {idx}",
                    "url": minuta.archivo.url,
                }
            )
    return documentos


def _tramites_list_base_queryset():
    return models.TramiteCaso.objects.select_related(
        "caso",
        "tipo",
        "estatus",
        "solicitante",
        "dirigido_a",
        "caso__solicitante",
        "caso__dirigido_a",
    ).prefetch_related(
        Prefetch(
            "caso__trabajadores_caso",
            queryset=models.CasoTrabajador.objects.select_related("trabajador"),
        )
    )


class DocumentoPreviewDataView(LoginRequiredMixin, View):
    """Devuelve los documentos adjuntos para vista previa desde listados."""

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        tipo = (request.GET.get("tipo") or "").strip().lower()
        pk_raw = (request.GET.get("id") or "").strip()
        if not pk_raw.isdigit():
            return JsonResponse({"detail": "ID inválido."}, status=400)
        pk = int(pk_raw)

        if tipo == "caso":
            if not request.user.has_perm("licencias.view_casointerno"):
                return JsonResponse({"detail": "No autorizado."}, status=403)
            caso = get_object_or_404(
                models.CasoInterno.objects.prefetch_related("minutas_adjuntas"),
                pk=pk,
            )
            return JsonResponse(
                {
                    "tipo": "caso",
                    "id": caso.pk,
                    "titulo": f"Caso #{caso.pk}",
                    "documentos": _preview_documentos_caso(caso),
                }
            )

        if tipo == "tramite":
            if not request.user.has_perm("licencias.view_tramitecaso"):
                return JsonResponse({"detail": "No autorizado."}, status=403)
            tramite_qs = models.TramiteCaso.objects.select_related("caso").prefetch_related(
                "minutas_adjuntas"
            )
            tramite = get_object_or_404(tramite_qs, pk=pk)
            caso_raw = (request.GET.get("caso_id") or "").strip()
            if caso_raw and caso_raw.isdigit() and tramite.caso_id != int(caso_raw):
                raise Http404("El trámite no pertenece al caso indicado.")
            return JsonResponse(
                {
                    "tipo": "tramite",
                    "id": tramite.pk,
                    "titulo": f"Trámite #{tramite.pk} · Caso #{tramite.caso_id}",
                    "documentos": _preview_documentos_tramite(tramite),
                }
            )

        return JsonResponse({"detail": "Tipo no soportado."}, status=400)


def _crear_tramite_desde_caso(
    caso: models.CasoInterno,
    *,
    target_case: models.CasoInterno,
) -> models.TramiteCaso:
    tramite = models.TramiteCaso.objects.create(
        caso=target_case,
        cct=caso.cct,
        cct_nombre=caso.cct_nombre or "",
        cct_sistema=caso.cct_sistema or "",
        cct_modalidad=caso.cct_modalidad or "",
        asesor_cct=caso.asesor_cct or "",
        tipo=caso.tipo_inicial,
        estatus=None,
        tipo_violencia=caso.tipo_violencia,
        tipos_violencia_adicionales=caso.tipos_violencia_adicionales or [],
        solicitante=caso.solicitante,
        dirigido_a=caso.dirigido_a,
        fecha=caso.fecha_apertura,
        fecha_termino=caso.fecha_termino,
        numero_oficio=caso.numero_oficio or "",
        asunto=caso.asunto or "",
        observaciones=caso.observaciones_iniciales or "",
        generador_nombre=caso.generador_nombre or "",
        generador_iniciales=caso.generador_iniciales or "",
        generador_sexo=caso.generador_sexo or "",
        receptor_nombre=caso.receptor_nombre or "",
        receptor_iniciales=caso.receptor_iniciales or "",
        receptor_sexo=caso.receptor_sexo or "",
        receptores_adicionales=caso.receptores_adicionales or [],
        generadores_adicionales=caso.generadores_adicionales or [],
        incidencia_nombre_docente=caso.incidencia_nombre_docente or "",
        incidencia_afiliacion=caso.incidencia_afiliacion or "",
        incidencia_fecha_inicio=caso.incidencia_fecha_inicio,
        incidencia_fecha_termino=caso.incidencia_fecha_termino,
        incidencia_dias_otorgados=caso.incidencia_dias_otorgados,
        rangos_fechas_adicionales=caso.rangos_fechas_adicionales or [],
    )
    usuarios = list(caso.usuarios_involucrados.all())
    if usuarios:
        tramite.usuarios_involucrados.set(usuarios)
    if caso.minuta:
        models.MinutaTramite.objects.create(tramite=tramite, archivo=caso.minuta)
    for minuta in caso.minutas_adjuntas.all():
        models.MinutaTramite.objects.create(tramite=tramite, archivo=minuta.archivo)
    return tramite


def _crear_caso_desde_tramite(
    tramite: models.TramiteCaso,
    *,
    estatus: models.EstatusCaso,
    tipo_inicial: models.TipoProceso,
    fecha_apertura,
) -> models.CasoInterno:
    cct_obj = tramite.cct or tramite.caso.cct
    caso = models.CasoInterno.objects.create(
        cct=cct_obj,
        cct_nombre=tramite.cct_nombre or tramite.caso.cct_nombre,
        cct_sistema=tramite.cct_sistema or tramite.caso.cct_sistema,
        cct_modalidad=tramite.cct_modalidad or tramite.caso.cct_modalidad,
        asesor_cct=tramite.asesor_cct or tramite.caso.asesor_cct,
        descripcion_breve=tramite.asunto or tramite.caso.descripcion_breve,
        fecha_apertura=fecha_apertura,
        estatus=estatus,
        tipo_inicial=tipo_inicial,
        tipo_violencia=tramite.tipo_violencia,
        tipos_violencia_adicionales=tramite.tipos_violencia_adicionales or [],
        numero_oficio=tramite.numero_oficio or "",
        solicitante=tramite.solicitante,
        dirigido_a=tramite.dirigido_a,
        generador_nombre=tramite.generador_nombre or "",
        generador_iniciales=tramite.generador_iniciales or "",
        generador_sexo=tramite.generador_sexo or "",
        receptor_nombre=tramite.receptor_nombre or "",
        receptor_iniciales=tramite.receptor_iniciales or "",
        receptor_sexo=tramite.receptor_sexo or "",
        receptores_adicionales=tramite.receptores_adicionales or [],
        generadores_adicionales=tramite.generadores_adicionales or [],
        asunto=tramite.asunto or "",
        observaciones_iniciales=tramite.observaciones or "",
        fecha_termino=tramite.fecha_termino,
        incidencia_nombre_docente=tramite.incidencia_nombre_docente or "",
        incidencia_afiliacion=tramite.incidencia_afiliacion or "",
        incidencia_fecha_inicio=tramite.incidencia_fecha_inicio,
        incidencia_fecha_termino=tramite.incidencia_fecha_termino,
        incidencia_dias_otorgados=tramite.incidencia_dias_otorgados,
        rangos_fechas_adicionales=tramite.rangos_fechas_adicionales or [],
    )
    usuarios = list(tramite.usuarios_involucrados.all())
    if not usuarios:
        usuarios = list(tramite.caso.usuarios_involucrados.all())
    if usuarios:
        caso.usuarios_involucrados.set(usuarios)
    if tramite.minuta:
        models.MinutaCaso.objects.create(caso=caso, archivo=tramite.minuta)
    for minuta in tramite.minutas_adjuntas.all():
        models.MinutaCaso.objects.create(caso=caso, archivo=minuta.archivo)
    return caso


# --------------------------------------------------------------------------- #
# Vistas HTML (Django templates + HTMX)
# --------------------------------------------------------------------------- #


def registrar_cambio_estatus_caso(
    caso: models.CasoInterno,
    usuario,
    estatus_anterior: models.EstatusCaso | None,
    estatus_nuevo: models.EstatusCaso | None,
    comentario: str = "",
    fecha_estatus=None,
    *,
    notify: bool = True,
) -> None:
    """Registra en la bitácora cuando el estatus del trámite cambia."""
    estatus_nuevo_id = getattr(estatus_nuevo, "pk", None)
    if not estatus_nuevo_id:
        logger.info(
            (
                "Se omitió historial de estatus de caso sin estatus_nuevo válido. "
                "caso_id=%s valor=%r"
            ),
            caso.pk,
            estatus_nuevo,
        )
        return
    actor = usuario if getattr(usuario, "is_authenticated", False) else None
    historial = models.HistorialEstatusCaso.objects.create(
        caso=caso,
        estatus_anterior=estatus_anterior,
        estatus_nuevo=estatus_nuevo,
        fecha_estatus=fecha_estatus or timezone.localdate(),
        usuario=actor,
        comentario=comentario or "",
    )
    if notify:
        notifications.notificar_estatus_caso(
            caso=caso,
            estatus_anterior=estatus_anterior,
            estatus_nuevo=estatus_nuevo,
            comentario=comentario or "",
        )
    inbox.notificar_caso_estatus(
        caso=caso,
        estatus_anterior=estatus_anterior,
        estatus_nuevo=estatus_nuevo,
        comentario=comentario or "",
        actor=actor,
    )
    auditoria.registrar_cambio_critico(
        modulo="estatus",
        accion="cambio_estatus",
        descripcion=f"Estatus de caso actualizado · Caso {caso.pk}",
        antes={"estatus_id": estatus_anterior.pk if estatus_anterior else None},
        despues={
            "estatus_id": estatus_nuevo.pk if estatus_nuevo else None,
            "comentario": comentario or "",
        },
        metadata={"tipo": "caso", "historial_id": historial.pk},
        actor=actor,
        instancia=historial,
        caso_id=caso.pk,
    )


def registrar_cambio_estatus_tramite(
    tramite: models.TramiteCaso,
    usuario,
    estatus_anterior: models.EstatusTramite | None,
    estatus_nuevo: models.EstatusTramite | None,
    comentario: str = "",
    fecha_estatus=None,
    *,
    notify: bool = True,
) -> None:
    """Guarda el historial cuando cambia el estatus de un trámite asociado."""
    estatus_nuevo_id = getattr(estatus_nuevo, "pk", None)
    if not estatus_nuevo_id:
        logger.info(
            (
                "Se omitió historial de estatus de trámite sin estatus_nuevo válido. "
                "tramite_id=%s valor=%r"
            ),
            tramite.pk,
            estatus_nuevo,
        )
        return
    actor = usuario if getattr(usuario, "is_authenticated", False) else None
    historial = models.HistorialEstatusTramiteCaso.objects.create(
        tramite=tramite,
        estatus_anterior=estatus_anterior,
        estatus_nuevo=estatus_nuevo,
        fecha_estatus=fecha_estatus or timezone.localdate(),
        usuario=actor,
        comentario=comentario or "",
    )
    inbox.notificar_tramite_estatus(
        tramite=tramite,
        estatus_anterior=estatus_anterior,
        estatus_nuevo=estatus_nuevo,
        comentario=comentario or "",
        actor=actor,
    )
    auditoria.registrar_cambio_critico(
        modulo="estatus",
        accion="cambio_estatus",
        descripcion=f"Estatus de trámite actualizado · Trámite {tramite.pk}",
        antes={"estatus_id": estatus_anterior.pk if estatus_anterior else None},
        despues={
            "estatus_id": estatus_nuevo.pk if estatus_nuevo else None,
            "comentario": comentario or "",
        },
        metadata={"tipo": "tramite", "historial_id": historial.pk},
        actor=actor,
        instancia=historial,
        caso_id=tramite.caso_id,
        tramite_id=tramite.pk,
    )


def registrar_cambio_estatus_licencia(
    licencia: models.LicenciaRegistro,
    usuario,
    estatus_anterior: models.EstatusLicencia | None,
    estatus_nuevo: models.EstatusLicencia | None,
    comentario: str = "",
    *,
    notify: bool = False,
) -> None:
    """Guarda el historial cuando cambia el estatus de una licencia."""
    estatus_nuevo_id = getattr(estatus_nuevo, "pk", None)
    if not estatus_nuevo_id:
        logger.info(
            (
                "Se omitió historial de estatus de licencia sin estatus_nuevo válido. "
                "licencia_id=%s valor=%r"
            ),
            licencia.pk,
            estatus_nuevo,
        )
        return
    actor = usuario if getattr(usuario, "is_authenticated", False) else None
    historial = models.HistorialEstatusLicencia.objects.create(
        licencia=licencia,
        estatus_anterior=estatus_anterior,
        estatus_nuevo=estatus_nuevo,
        usuario=actor,
        comentario=comentario or "",
    )
    if notify:
        logger.info(
            "Notificación de estatus de licencia omitida (canal no definido). licencia_id=%s",
            licencia.pk,
        )
    auditoria.registrar_cambio_critico(
        modulo="estatus",
        accion="cambio_estatus",
        descripcion=f"Estatus de licencia actualizado · Licencia {licencia.pk}",
        antes={"estatus_id": estatus_anterior.pk if estatus_anterior else None},
        despues={
            "estatus_id": estatus_nuevo.pk if estatus_nuevo else None,
            "comentario": comentario or "",
        },
        metadata={"tipo": "licencia", "historial_id": historial.pk},
        actor=actor,
        instancia=historial,
        licencia_id=licencia.pk,
    )


def obtener_estatus_actual_tramite(tramite: models.TramiteCaso) -> models.EstatusTramite | None:
    """Resuelve el estatus actual del trámite según su historial."""
    ultimo = tramite.historial_estatus.order_by("-fecha_cambio", "-id").first()
    return ultimo.estatus_nuevo if ultimo else None


def obtener_estatus_actual_caso(caso: models.CasoInterno) -> models.EstatusCaso | None:
    """Resuelve el estatus actual del caso según su historial."""
    ultimo = caso.historial_estatus.order_by("-fecha_cambio", "-id").first()
    return ultimo.estatus_nuevo if ultimo else None


def _build_trabajadores_resumen(caso: models.CasoInterno) -> list[dict[str, Any]]:
    relaciones = list(
        caso.trabajadores_caso.select_related("trabajador", "centro_trabajo_preferido")
    )
    resumenes = []
    for relacion in relaciones:
        info = get_latest_registro_info(relacion.trabajador_id)
        resumenes.append(
            {
                "trabajador": relacion.trabajador,
                "es_principal": relacion.es_principal,
                "centro_preferido": relacion.centro_trabajo_preferido,
                "ultimo_ciclo": info.get("ultimo_ciclo") or "",
                "ultimo_anio": info.get("ultimo_anio"),
                "centros": info.get("centros", []),
                "registros": info.get("registros", []),
            }
        )
    manuales = caso.trabajadores_manuales or []
    if isinstance(manuales, list):
        for item in manuales:
            if not isinstance(item, dict):
                continue
            nombre = str(item.get("nombre") or "").strip()
            if not nombre:
                continue
            resumenes.append(
                {
                    "trabajador": SimpleNamespace(
                        id=item.get("id") or "",
                        nombre=nombre,
                        rfc=str(item.get("rfc") or "").strip(),
                        curp=str(item.get("curp") or "").strip(),
                    ),
                    "es_principal": False,
                    "centro_preferido": None,
                    "ultimo_ciclo": "",
                    "ultimo_anio": None,
                    "centros": [],
                    "registros": [],
                    "es_manual": True,
                }
            )
    return resumenes


def _collect_trabajadores_nombres(caso: models.CasoInterno) -> tuple[list[str], str]:
    relaciones = list(caso.trabajadores_caso.all())
    relaciones.sort(
        key=lambda rel: (
            0 if rel.es_principal else 1,
            ((rel.trabajador.nombre or "").strip().lower() if rel.trabajador_id and rel.trabajador else ""),
        )
    )
    nombres: list[str] = []
    seen: set[str] = set()
    principal_nombre = ""

    def _append_nombre(value: str) -> None:
        nombre = (value or "").strip()
        if not nombre:
            return
        key = nombre.lower()
        if key in seen:
            return
        seen.add(key)
        nombres.append(nombre)

    for relacion in relaciones:
        if relacion.trabajador_id and relacion.trabajador:
            nombre_relacion = (relacion.trabajador.nombre or "").strip()
            _append_nombre(nombre_relacion)
            if relacion.es_principal and nombre_relacion and not principal_nombre:
                principal_nombre = nombre_relacion

    manuales = caso.trabajadores_manuales or []
    if isinstance(manuales, list):
        for item in manuales:
            if not isinstance(item, dict):
                continue
            _append_nombre(str(item.get("nombre") or ""))

    if not principal_nombre and nombres:
        principal_nombre = nombres[0]
    return nombres, principal_nombre


def _build_trabajadores_listado(caso: models.CasoInterno) -> str:
    nombres, _principal_nombre = _collect_trabajadores_nombres(caso)
    if nombres:
        return " · ".join(nombres)
    incidencia_nombre = str(caso.incidencia_nombre_docente or "").strip()
    return incidencia_nombre or "-"


def _catalogo_nombre(item: Any) -> str:
    if not item:
        return "-"
    nombre = str(getattr(item, "nombre", "") or "").strip()
    return nombre or "-"


def _catalogo_nombre_fallback(*items: Any) -> str:
    for item in items:
        nombre = _catalogo_nombre(item)
        if nombre != "-":
            return nombre
    return "-"


def _extract_participantes_adicionales_nombres(adicionales: Any) -> list[str]:
    if not isinstance(adicionales, list):
        return []
    nombres: list[str] = []
    seen: set[str] = set()
    for item in adicionales:
        nombre = ""
        if isinstance(item, dict):
            nombre = str(item.get("nombre") or "").strip()
            if not nombre:
                nombre = str(item.get("iniciales") or "").strip()
        elif isinstance(item, str):
            nombre = item.strip()
        if not nombre:
            continue
        key = nombre.lower()
        if key in seen:
            continue
        seen.add(key)
        nombres.append(nombre)
    return nombres


def _build_participante_listado(principal_nombre: str, adicionales: Any) -> tuple[str, int]:
    principal = str(principal_nombre or "").strip()
    adicionales_nombres = _extract_participantes_adicionales_nombres(adicionales)
    if principal:
        total = 1 + len(adicionales_nombres)
        return principal, max(total - 1, 0)
    if adicionales_nombres:
        total = len(adicionales_nombres)
        return adicionales_nombres[0], max(total - 1, 0)
    return "-", 0


def _tramite_post_has_worker_payload(form: forms.TramiteCasoForm, data) -> bool:
    prefix = form.prefix or ""
    names = (
        "trabajador_principal",
        "trabajador_principal_nombre",
        "trabajadores_adicionales",
        "trabajadores_centros",
        "trabajadores_manuales",
    )
    for name in names:
        key = f"{prefix}-{name}" if prefix else name
        if key in data:
            return True
    return False


def _build_aviso_cct_mismatch(
    caso: models.CasoInterno, resumenes: list[dict[str, Any]]
) -> dict[str, Any] | None:
    principal = next((item for item in resumenes if item.get("es_principal")), None)
    if not principal:
        return None
    centros = principal.get("centros") or []
    if not centros:
        return None
    ccts = {centro.get("cct") for centro in centros if centro.get("cct")}
    if caso.cct_id and caso.cct_id not in ccts:
        return {
            "cct_caso": caso.cct_id,
            "cct_caso_nombre": caso.cct_nombre,
            "ultimo_ciclo": principal.get("ultimo_ciclo") or "",
            "ultimo_anio": principal.get("ultimo_anio"),
            "centros": centros,
        }
    return None


def _guardar_minutas_caso(caso: models.CasoInterno, archivos: list) -> None:
    for archivo in archivos:
        models.MinutaCaso.objects.create(caso=caso, archivo=archivo)


def _guardar_minutas_tramite(tramite: models.TramiteCaso, archivos: list) -> None:
    for archivo in archivos:
        models.MinutaTramite.objects.create(tramite=tramite, archivo=archivo)


class FeatureFlagRequiredMixin:
    """Bloquea una vista cuando un feature flag de módulo está deshabilitado."""

    feature_flag_code: str | None = None
    feature_flag_default: bool = True

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        code = getattr(self, "feature_flag_code", None)
        if code and not feature_flags.is_enabled(
            code,
            request.user,
            default_if_missing=self.feature_flag_default,
        ):
            messages.error(
                request,
                _("El módulo solicitado está deshabilitado para tu rol."),
            )
            return redirect("tramites:home")
        return super().dispatch(request, *args, **kwargs)


class LicenciasFeatureFlagMixin(FeatureFlagRequiredMixin):
    feature_flag_code = "module_licencias"


class ReportesFeatureFlagMixin(FeatureFlagRequiredMixin):
    feature_flag_code = "module_reportes"




class ToolIndexView(FeatureFlagRequiredMixin, LoginRequiredMixin, TemplateView):
    """Índice de herramientas auxiliares."""

    template_name = "tramites/herramientas/index.html"
    feature_flag_code = "module_herramientas"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        can_use_herramientas = feature_flags.is_enabled("module_herramientas", self.request.user)
        can_use_gobierno = feature_flags.is_enabled("module_gobierno_datos", self.request.user)
        ctx["tools"] = [
            *(
                [
                    {
                        "title": "Gestión de folios",
                        "description": "Genera y administra folios con control de consecutivo y auditoría.",
                        "url": reverse_lazy("tramites:folio-list"),
                        "badge": "Folio",
                    }
                ]
                if self.request.user.has_perm("licencias.view_folioregistro")
                and feature_flags.is_enabled("module_tramites", self.request.user)
                else []
            ),
            {
                "title": "Analizador de requisitos del trámite",
                "description": "Calcula los días válidos de licencias médicas y verifica los 15 años de servicio.",
                "url": reverse_lazy("tramites:analizador-tramite"),
                "badge": "Cálculo",
            },
            {
                "title": "Consulta de plantillas de secundarias",
                "description": "Busca empleados y centros de trabajo registrados por ciclo escolar.",
                "url": reverse_lazy("tramites:plantillas-secundarias"),
                "badge": "Consulta",
            },
            *(
                [
                    {
                        "title": "Gobierno de datos",
                        "description": "Administra feature flags, eventos, calidad de datos y jobs programados.",
                        "url": reverse_lazy("tramites:gobierno-datos"),
                        "badge": "E1",
                    }
                ]
                if self.request.user.has_perm("licencias.view_eventosistema") and can_use_gobierno
                else []
            ),
        ]
        if not can_use_herramientas:
            ctx["tools"] = []
        return ctx


class HomeView(LoginRequiredMixin, TemplateView):
    """Panel operativo por rol con foco en trabajo diario."""

    template_name = "tramites/dashboard.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        snapshot = operacion.build_user_operation_snapshot(
            self.request.user,
            queue_limit=8,
            panel_limit=5,
        )
        can_change_casos = self.request.user.has_perm("licencias.change_casointerno")
        can_change_tramites = self.request.user.has_perm("licencias.change_tramitecaso")
        saved_filters = list(
            models.FiltroGuardadoUsuario.objects.filter(
                usuario=self.request.user,
                alcance=models.FiltroGuardadoUsuario.ALCANCE_CASOS_LISTADO,
            ).order_by("nombre")[:8]
        )
        for filtro in saved_filters:
            query_string = _sanitize_saved_filter_querystring(
                filtro.query_string,
                allowed_keys=FILTROS_GUARDADOS_KEYS_CASOS,
            )
            filtro.apply_url = (
                f"{reverse_lazy('tramites:casointerno-list')}?{query_string}"
                if query_string
                else reverse_lazy("tramites:casointerno-list")
            )

        group_names = list(self.request.user.groups.order_by("name").values_list("name", flat=True))
        ctx.update(
            {
                "snapshot_operacion": snapshot,
                "can_change_casos": can_change_casos,
                "can_change_tramites": can_change_tramites,
                "operation_estatus_caso": list(
                    models.EstatusCaso.objects.order_by("orden", "nombre").values("id", "nombre")
                ),
                "operation_estatus_tramite": list(
                    models.EstatusTramite.objects.order_by("orden", "nombre").values("id", "nombre")
                ),
                "operation_assignable_users": _operacion_assignable_users(),
                "saved_filters_casos": saved_filters,
                "rol_activo": ", ".join(group_names) if group_names else "Sin rol explícito",
                "operacion_next_url": self.request.get_full_path(),
            }
        )
        return ctx


class FiltroGuardadoUsuarioView(LoginRequiredMixin, View):
    """Gestiona creación y eliminación de filtros guardados por usuario."""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        fallback = reverse_lazy("tramites:casointerno-list")
        next_url = _resolve_next_url(request, fallback=str(fallback))
        action = (request.POST.get("action") or "").strip()
        if action == "save":
            form = forms.FiltroGuardadoOperacionForm(request.POST)
            if not form.is_valid():
                messages.error(request, _("No fue posible guardar el filtro."))
                return redirect(next_url)
            alcance = (form.cleaned_data.get("alcance") or "").strip()
            allowed_keys = (
                FILTROS_GUARDADOS_KEYS_COLA
                if alcance == models.FiltroGuardadoUsuario.ALCANCE_COLA_TRABAJO
                else FILTROS_GUARDADOS_KEYS_CASOS
            )
            query_string = _sanitize_saved_filter_querystring(
                form.cleaned_data.get("querystring") or "",
                allowed_keys=allowed_keys,
            )
            if not query_string:
                messages.error(request, _("Aplica al menos un filtro para poder guardarlo."))
                return redirect(next_url)
            filtro, created = models.FiltroGuardadoUsuario.objects.update_or_create(
                usuario=request.user,
                alcance=alcance or models.FiltroGuardadoUsuario.ALCANCE_CASOS_LISTADO,
                nombre=form.cleaned_data["nombre"].strip(),
                defaults={"query_string": query_string},
            )
            auditoria.registrar_evento(
                categoria="sistema",
                accion="actualizado",
                descripcion=(
                    f"Filtro guardado {'creado' if created else 'actualizado'}: {filtro.nombre}."
                ),
                metadata={
                    "scope": filtro.alcance,
                    "filter_id": filtro.pk,
                    "query_string": filtro.query_string,
                },
                actor=request.user,
            )
            messages.success(
                request,
                _("Filtro guardado correctamente.")
                if created
                else _("Filtro actualizado correctamente."),
            )
            return redirect(next_url)

        if action == "delete":
            filtro_id_raw = (request.POST.get("filter_id") or "").strip()
            if not filtro_id_raw.isdigit():
                messages.error(request, _("Filtro inválido."))
                return redirect(next_url)
            filtro = get_object_or_404(
                models.FiltroGuardadoUsuario,
                pk=int(filtro_id_raw),
                usuario=request.user,
            )
            filtro_nombre = filtro.nombre
            filtro_alcance = filtro.alcance
            filtro.delete()
            auditoria.registrar_evento(
                categoria="sistema",
                accion="eliminado",
                descripcion=f"Filtro guardado eliminado: {filtro_nombre}.",
                metadata={"scope": filtro_alcance},
                actor=request.user,
            )
            messages.success(request, _("Filtro eliminado."))
            return redirect(next_url)

        messages.error(request, _("Acción no soportada."))
        return redirect(next_url)


class OperacionAccionRapidaView(LoginRequiredMixin, View):
    """Ejecuta acciones rápidas de asignación y cambio de estatus."""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        fallback = reverse_lazy("tramites:home")
        next_url = _resolve_next_url(request, fallback=str(fallback))
        form = forms.OperacionAccionRapidaForm(request.POST)
        if not form.is_valid():
            messages.error(request, _("No fue posible completar la acción rápida."))
            return redirect(next_url)

        action = form.cleaned_data["action"]
        target_type = form.cleaned_data["target_type"]
        target_id = form.cleaned_data["target_id"]
        comentario = (form.cleaned_data.get("comentario") or "").strip()

        if target_type == forms.OperacionAccionRapidaForm.TARGET_CASE:
            target = get_object_or_404(models.CasoInterno.objects.select_related("estatus"), pk=target_id)
            permission = "licencias.change_casointerno"
            modulo = "caso"
        else:
            target = get_object_or_404(
                models.TramiteCaso.objects.select_related("estatus", "caso"),
                pk=target_id,
            )
            permission = "licencias.change_tramitecaso"
            modulo = "tramite"

        if not request.user.has_perm(permission):
            raise DjangoPermissionDenied("No tienes permiso para ejecutar esta acción.")

        if action == forms.OperacionAccionRapidaForm.ACTION_ASSIGN:
            usuario_obj = form.cleaned_data["usuario_asignado"]
            before_ids = sorted(target.usuarios_involucrados.values_list("id", flat=True))
            target.usuarios_involucrados.add(usuario_obj)
            after_ids = sorted(target.usuarios_involucrados.values_list("id", flat=True))
            if before_ids == after_ids:
                messages.info(request, _("El usuario ya estaba asignado al registro."))
                return redirect(next_url)
            auditoria.registrar_cambio_critico(
                modulo=modulo,
                accion="actualizado",
                descripcion="Asignación rápida de usuario involucrado.",
                antes={"usuarios_involucrados": before_ids},
                despues={"usuarios_involucrados": after_ids},
                actor=request.user,
                instancia=target,
                metadata={
                    "source": "operacion_rapida",
                    "action": "asignar",
                    "usuario_asignado": usuario_obj.pk,
                },
            )
            messages.success(
                request,
                _("Usuario asignado correctamente."),
            )
            return redirect(next_url)

        if action == forms.OperacionAccionRapidaForm.ACTION_STATUS:
            if target_type == forms.OperacionAccionRapidaForm.TARGET_CASE:
                nuevo_estatus = form.cleaned_data["estatus_caso"]
                if target.estatus_id == nuevo_estatus.pk:
                    messages.info(request, _("El caso ya tiene ese estatus."))
                    return redirect(next_url)
                registrar_cambio_estatus_caso(
                    caso=target,
                    usuario=request.user,
                    estatus_anterior=target.estatus,
                    estatus_nuevo=nuevo_estatus,
                    comentario=comentario,
                    notify=True,
                )
                target.estatus = nuevo_estatus
                target.save(update_fields=["estatus", "actualizado_en"])
                messages.success(request, _("Estatus de caso actualizado."))
            else:
                nuevo_estatus = form.cleaned_data["estatus_tramite"]
                if target.estatus_id == nuevo_estatus.pk:
                    messages.info(request, _("El trámite ya tiene ese estatus."))
                    return redirect(next_url)
                registrar_cambio_estatus_tramite(
                    tramite=target,
                    usuario=request.user,
                    estatus_anterior=target.estatus,
                    estatus_nuevo=nuevo_estatus,
                    comentario=comentario,
                    notify=True,
                )
                target.estatus = nuevo_estatus
                target.save(update_fields=["estatus", "actualizado_en"])
                messages.success(request, _("Estatus de trámite actualizado."))
            return redirect(next_url)

        messages.error(request, _("Acción rápida no soportada."))
        return redirect(next_url)


class MiColaTrabajoView(LoginRequiredMixin, TemplateView):
    """Vista priorizada de trabajo diario para el usuario autenticado."""

    template_name = "tramites/mi_cola_trabajo.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        tipo = (self.request.GET.get("tipo") or "").strip()
        prioridad = (self.request.GET.get("prioridad") or "").strip()
        estado = (self.request.GET.get("estado") or "").strip()
        snapshot = operacion.build_user_operation_snapshot(
            self.request.user,
            queue_limit=250,
            panel_limit=6,
        )
        queue_items = operacion.filter_queue_items(
            snapshot["all_items"],
            tipo=tipo,
            prioridad=prioridad,
            estado=estado,
        )
        current_querystring = _build_saved_filter_querystring_from_request(
            self.request,
            allowed_keys=FILTROS_GUARDADOS_KEYS_COLA,
        )
        filtros_guardados = list(
            models.FiltroGuardadoUsuario.objects.filter(
                usuario=self.request.user,
                alcance=models.FiltroGuardadoUsuario.ALCANCE_COLA_TRABAJO,
            ).order_by("nombre")
        )
        for filtro in filtros_guardados:
            query_string = _sanitize_saved_filter_querystring(
                filtro.query_string,
                allowed_keys=FILTROS_GUARDADOS_KEYS_COLA,
            )
            filtro.apply_url = (
                f"{reverse_lazy('tramites:mi-cola')}?{query_string}"
                if query_string
                else reverse_lazy("tramites:mi-cola")
            )

        ctx.update(
            {
                "snapshot_operacion": snapshot,
                "cola_items": queue_items,
                "cola_filters": {
                    "tipo": tipo,
                    "prioridad": prioridad,
                    "estado": estado,
                },
                "can_change_casos": self.request.user.has_perm("licencias.change_casointerno"),
                "can_change_tramites": self.request.user.has_perm("licencias.change_tramitecaso"),
                "operation_estatus_caso": list(
                    models.EstatusCaso.objects.order_by("orden", "nombre").values("id", "nombre")
                ),
                "operation_estatus_tramite": list(
                    models.EstatusTramite.objects.order_by("orden", "nombre").values("id", "nombre")
                ),
                "operation_assignable_users": _operacion_assignable_users(),
                "operacion_next_url": self.request.get_full_path(),
                "saved_filters_cola": filtros_guardados,
                "saved_filter_form_cola": forms.FiltroGuardadoOperacionForm(
                    initial={
                        "alcance": models.FiltroGuardadoUsuario.ALCANCE_COLA_TRABAJO,
                        "querystring": current_querystring,
                    }
                ),
                "saved_filters_cola_querystring": current_querystring,
            }
        )
        return ctx


class BandejaEntradaListView(LoginRequiredMixin, ListView):
    """Bandeja de entrada de notificaciones internas."""

    model = models.BandejaNotificacionDestinatario
    template_name = "tramites/notificaciones/inbox.html"
    context_object_name = "entradas"
    paginate_by = 20

    def _build_filter_url(self, **updates: str) -> str:
        params = self.request.GET.copy()
        for key, value in updates.items():
            if value in (None, ""):
                params.pop(key, None)
            else:
                params[key] = value
        params.pop("page", None)
        base_url = str(reverse_lazy("tramites:bandeja"))
        query = params.urlencode()
        return f"{base_url}?{query}" if query else base_url

    def get_queryset(self):
        modo = (self.request.GET.get("modo") or "").strip()
        orden = (self.request.GET.get("orden") or "recientes").strip()
        has_filters = any(
            (self.request.GET.get(key) or "").strip()
            for key in ("q", "estado", "evento", "tipo", "desde", "hasta", "orden")
        )
        qs = (
            super()
            .get_queryset()
            .filter(usuario=self.request.user)
            .select_related(
                "notificacion",
                "notificacion__actor",
                "notificacion__caso",
                "notificacion__tramite",
                "notificacion__tramite__caso",
            )
        )
        if not has_filters and modo != "todas":
            qs = qs.filter(notificacion__evento="caso_creado")
        query = (self.request.GET.get("q") or "").strip()
        if query:
            qs = qs.filter(
                Q(notificacion__titulo__icontains=query)
                | Q(notificacion__mensaje__icontains=query)
                | Q(notificacion__referencia__icontains=query)
                | Q(notificacion__caso__numero_oficio__icontains=query)
                | Q(notificacion__tramite__numero_oficio__icontains=query)
            )
        estado = (self.request.GET.get("estado") or "").strip()
        if estado == "no_leidas":
            qs = qs.filter(leido=False)
        evento = (self.request.GET.get("evento") or "").strip()
        if evento:
            qs = qs.filter(notificacion__evento=evento)
        tipo = (self.request.GET.get("tipo") or "").strip()
        if tipo == "caso":
            qs = qs.filter(notificacion__caso__isnull=False, notificacion__tramite__isnull=True)
        elif tipo == "tramite":
            qs = qs.filter(notificacion__tramite__isnull=False)
        elif tipo == "estatus":
            qs = qs.filter(notificacion__evento__icontains="estatus")
        desde = (self.request.GET.get("desde") or "").strip()
        hasta = (self.request.GET.get("hasta") or "").strip()
        if desde:
            qs = qs.filter(notificacion__creado_en__date__gte=desde)
        if hasta:
            qs = qs.filter(notificacion__creado_en__date__lte=hasta)
        if orden == "antiguas":
            qs = qs.order_by("notificacion__creado_en", "notificacion__id", "id")
        else:
            qs = qs.order_by("-notificacion__creado_en", "-notificacion__id", "-id")
        return qs

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["eventos"] = models.BandejaNotificacion.EVENTO_CHOICES
        ctx["modo"] = self.request.GET.get("modo", "")
        ctx["estado"] = self.request.GET.get("estado", "")
        ctx["evento"] = self.request.GET.get("evento", "")
        ctx["desde"] = self.request.GET.get("desde", "")
        ctx["hasta"] = self.request.GET.get("hasta", "")
        ctx["q"] = self.request.GET.get("q", "")
        ctx["tipo"] = self.request.GET.get("tipo", "")
        ctx["orden"] = self.request.GET.get("orden", "recientes")
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["inbox_query"] = params.urlencode()
        ctx["inbox_url_todas"] = self._build_filter_url(modo="todas", evento="", tipo="")
        ctx["inbox_url_tipo_caso"] = self._build_filter_url(tipo="caso")
        ctx["inbox_url_tipo_tramite"] = self._build_filter_url(tipo="tramite")
        ctx["inbox_url_tipo_estatus"] = self._build_filter_url(tipo="estatus")
        ctx["inbox_url_no_leidas"] = self._build_filter_url(estado="no_leidas")
        ctx["inbox_url_evento_caso_creado"] = self._build_filter_url(
            modo="",
            evento="caso_creado",
        )
        return ctx


class BandejaEntradaMarcarTodoView(LoginRequiredMixin, View):
    """Marca todas las notificaciones como leídas."""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        inbox.marcar_notificaciones_leidas(usuario=request.user)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        messages.success(request, _("Bandeja marcada como leída."))
        return redirect("tramites:bandeja")


class BandejaEntradaMarcarView(LoginRequiredMixin, View):
    """Marca una notificación específica como leída para el usuario."""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        destinatario = get_object_or_404(
            models.BandejaNotificacionDestinatario,
            pk=kwargs.get("pk"),
            usuario=request.user,
        )
        if not destinatario.leido:
            destinatario.leido = True
            destinatario.leido_en = timezone.now()
            destinatario.save(update_fields=["leido", "leido_en"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "pk": destinatario.pk})
        return redirect(request.POST.get("next") or "tramites:bandeja")


class TramiteEligibilityToolView(FeatureFlagRequiredMixin, LoginRequiredMixin, TemplateView):
    """Muestra la herramienta de cálculo de requisitos del trámite."""

    template_name = "tramites/herramientas/analizador_tramite.html"
    feature_flag_code = "module_herramientas"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "today": timezone.localdate(),
                "minimum_years": 15,
                "regimen_choices": [
                    {"value": "issste", "label": "ISSSTE · 60 días requeridos", "days": 60},
                    {"value": "imss", "label": "IMSS · 90 días requeridos", "days": 90},
                ],
            }
        )
        return ctx


class PlantillaSecundariasToolView(FeatureFlagRequiredMixin, LoginRequiredMixin, TemplateView):
    """Muestra la herramienta de consulta de plantillas de secundarias."""

    template_name = "tramites/herramientas/plantillas_secundarias.html"
    partial_template_name = "tramites/herramientas/partials/plantillas_resultados.html"
    feature_flag_code = "module_herramientas"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()
        cct_query = (self.request.GET.get("cct") or "").strip()
        ciclo_query = (self.request.GET.get("ciclo") or "").strip()

        ctx.update(
            {
                "query": query,
                "cct_query": cct_query,
                "ciclo_query": ciclo_query,
                "resultados": [],
                "resultados_agrupados": [],
                "resultados_total": 0,
                "limite_excedido": False,
            }
        )

        if not (query or cct_query or ciclo_query):
            return ctx

        latest_anio = models.PlantillaRegistro.objects.filter(
            empleado=dj_models.OuterRef("empleado")
        ).order_by(
            "-anio",
            "-ciclo",
        ).values("anio")[:1]

        latest_ciclo = models.PlantillaRegistro.objects.filter(
            empleado=dj_models.OuterRef("empleado")
        ).order_by(
            "-anio",
            "-ciclo",
        ).values("ciclo")[:1]

        qs = (
            models.PlantillaRegistro.objects.select_related("centro_trabajo", "empleado")
            .prefetch_related("claves")
            .annotate(ultimo_anio=dj_models.Subquery(latest_anio))
            .annotate(ultimo_ciclo=dj_models.Subquery(latest_ciclo))
        )

        if query:
            qs = qs.filter(
                dj_models.Q(empleado__nombre__icontains=query)
                | dj_models.Q(empleado__rfc__icontains=query)
                | dj_models.Q(empleado__curp__icontains=query)
            )
        if cct_query:
            qs = qs.filter(
                dj_models.Q(centro_trabajo__cct__icontains=cct_query)
                | dj_models.Q(centro_trabajo__nombre__icontains=cct_query)
            )
        if ciclo_query:
            qs = qs.filter(ciclo__icontains=ciclo_query)

        limite = 50
        total = qs.count()
        ctx["resultados_total"] = total
        if total > limite:
            ctx["limite_excedido"] = True

        resultados = list(qs.order_by("empleado__nombre", "-anio", "-ciclo")[:limite])
        ctx["resultados"] = resultados
        agrupados = []
        indice = {}
        for registro in resultados:
            key = (registro.empleado_id, registro.ciclo)
            grupo = indice.get(key)
            if not grupo:
                grupo = {
                    "empleado": registro.empleado,
                    "ciclo": registro.ciclo,
                    "ultimo_ciclo": registro.ultimo_ciclo,
                    "ultimo_anio": registro.ultimo_anio,
                    "registros": [],
                    "centros": [],
                    "centros_seen": set(),
                }
                indice[key] = grupo
                agrupados.append(grupo)
            grupo["registros"].append(registro)
            cct = registro.centro_trabajo.cct
            if cct and cct not in grupo["centros_seen"]:
                grupo["centros_seen"].add(cct)
                grupo["centros"].append(
                    {
                        "cct": cct,
                        "nombre": registro.centro_trabajo.nombre,
                        "asesor": registro.centro_trabajo.asesor,
                    }
                )
        ctx["resultados_agrupados"] = agrupados
        return ctx

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        context = self.get_context_data(**kwargs)
        wants_partial = request.headers.get("HX-Request") == "true" or request.GET.get("partial") == "1"
        if wants_partial:
            return render(request, self.partial_template_name, context)
        return render(request, self.template_name, context)


class DataGovernanceView(FeatureFlagRequiredMixin, LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Panel E1 de gobierno de datos: flags, jobs, auditoría y calidad."""

    template_name = "tramites/herramientas/gobierno_datos.html"
    permission_required = "licencias.view_eventosistema"
    feature_flag_code = "module_gobierno_datos"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        action = (request.POST.get("action") or "").strip()
        if action == "flag-global":
            if not request.user.has_perm("licencias.change_featureflag"):
                raise DjangoPermissionDenied("No tienes permiso para actualizar feature flags.")
            flag = get_object_or_404(models.FeatureFlag, pk=request.POST.get("flag_id"))
            flag.habilitado = request.POST.get("enabled") == "1"
            flag.habilitado_por_defecto = request.POST.get("default_enabled") == "1"
            flag.save(update_fields=["habilitado", "habilitado_por_defecto", "actualizado_en"])
            messages.success(request, _("Feature flag actualizada."))

        elif action == "flag-grupo":
            if not request.user.has_perm("licencias.change_featureflaggrupo"):
                raise DjangoPermissionDenied("No tienes permiso para actualizar reglas por grupo.")
            flag = get_object_or_404(models.FeatureFlag, pk=request.POST.get("flag_id"))
            grupo = get_object_or_404(Group, pk=request.POST.get("group_id"))
            habilitado = request.POST.get("enabled") == "1"
            regla, creada = models.FeatureFlagGrupo.objects.get_or_create(flag=flag, grupo=grupo)
            regla.habilitado = habilitado
            regla.actualizado_por = request.user
            regla.save(update_fields=["habilitado", "actualizado_por", "actualizado_en"])
            if creada:
                messages.success(request, _("Regla por grupo creada."))
            else:
                messages.success(request, _("Regla por grupo actualizada."))

        elif action == "quality-run":
            if not request.user.has_perm("licencias.add_dataqualityrun"):
                raise DjangoPermissionDenied("No tienes permiso para ejecutar calidad de datos.")
            run = data_quality.run_quality_scan(actor=request.user, origen="manual")
            messages.success(
                request,
                _(
                    "Corrida completada. Hallazgos detectados: %(total)s."
                )
                % {"total": run.resumen.get("issues_detected", 0)},
            )

        elif action == "jobs-schedule":
            if not request.user.has_perm("licencias.add_asyncjob"):
                raise DjangoPermissionDenied("No tienes permiso para programar jobs.")
            created = jobs.schedule_due_jobs()
            messages.success(request, _("Jobs encolados: %(total)s.") % {"total": len(created)})

        elif action == "jobs-run":
            if not request.user.has_perm("licencias.change_asyncjob"):
                raise DjangoPermissionDenied("No tienes permiso para ejecutar jobs.")
            limit_raw = (request.POST.get("limit") or "10").strip()
            try:
                limit = max(1, min(100, int(limit_raw)))
            except (TypeError, ValueError):
                limit = 10
            processed = jobs.run_pending_jobs(limit=limit, worker_name=f"web-{request.user.pk}")
            messages.success(request, _("Jobs procesados: %(total)s.") % {"total": len(processed)})

        elif action == "jobs-enqueue-quality":
            if not request.user.has_perm("licencias.add_asyncjob"):
                raise DjangoPermissionDenied("No tienes permiso para encolar jobs.")
            jobs.enqueue_job(
                job_type="data_quality_scan",
                payload={"source": "manual_ui"},
                creado_por=request.user,
            )
            messages.success(request, _("Job de calidad encolado."))

        return redirect("tramites:gobierno-datos")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        selected_group_id = (self.request.GET.get("group_id") or "").strip()
        grupos = list(Group.objects.order_by("name").only("id", "name"))
        if selected_group_id.isdigit():
            selected_group = next((grupo for grupo in grupos if grupo.pk == int(selected_group_id)), None)
        else:
            selected_group = grupos[0] if grupos else None

        flags = list(
            models.FeatureFlag.objects.prefetch_related(
                Prefetch(
                    "asignaciones_grupo",
                    queryset=models.FeatureFlagGrupo.objects.select_related("grupo").order_by("grupo__name"),
                )
            ).order_by("modulo", "codigo")
        )
        flag_matrix: dict[int, dict[int, models.FeatureFlagGrupo]] = {}
        for flag in flags:
            by_group = {regla.grupo_id: regla for regla in flag.asignaciones_grupo.all()}
            flag_matrix[flag.pk] = by_group
            if selected_group:
                setattr(flag, "selected_group_rule", by_group.get(selected_group.pk))
            else:
                setattr(flag, "selected_group_rule", None)

        latest_quality_run, quality_issues, quality_summary = data_quality.get_latest_report(issue_limit=150)
        eventos = list(
            models.EventoSistema.objects.select_related("actor", "content_type", "caso", "tramite", "licencia")
            .order_by("-creado_en", "-id")[:80]
        )
        cambios = list(
            models.BitacoraCambioCritico.objects.select_related(
                "actor", "content_type", "caso", "tramite", "licencia"
            )
            .order_by("-creado_en", "-id")[:80]
        )
        scheduled_jobs = list(models.ScheduledJob.objects.order_by("codigo"))
        recent_async_jobs = list(
            models.AsyncJob.objects.select_related("scheduled_job", "creado_por")
            .order_by("-creado_en", "-id")[:80]
        )

        ctx.update(
            {
                "feature_flags": flags,
                "feature_groups": grupos,
                "selected_group": selected_group,
                "feature_matrix": flag_matrix,
                "latest_quality_run": latest_quality_run,
                "quality_issues": quality_issues,
                "quality_summary": quality_summary,
                "eventos_sistema": eventos,
                "cambios_criticos": cambios,
                "scheduled_jobs": scheduled_jobs,
                "recent_async_jobs": recent_async_jobs,
            }
        )
        return ctx


class CCTCatalogContextMixin:
    """Proporciona en el contexto el catálogo y endpoints relacionados con CCT."""

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["plantilla_readonly"] = True
        readonly = ctx["plantilla_readonly"]
        ensure_cct_catalog_loaded()
        catalogo = list(
            models.PlantillaCentroTrabajo.objects.order_by("cct").values(
                "cct", "nombre", "subnivel", "asesor", "sostenimiento"
            )
        )
        for item in catalogo:
            item["sostenimiento"] = normalise_sistema(item.get("sostenimiento"))
            item["servicio"] = item.pop("subnivel", "") or ""
        ctx["cct_catalogo"] = catalogo
        ctx["cct_lookup_url"] = reverse_lazy("tramites:cct-lookup")
        ctx["cct_api_url"] = reverse_lazy("tramites_api:cct-list")
        ctx["empleado_lookup_url"] = reverse_lazy("tramites:empleado-lookup")
        ctx["empleado_picker_url"] = f"{reverse_lazy('tramites:empleado-picker')}?readonly=1"
        if readonly:
            ctx["empleado_centros_add_url"] = ""
            ctx["empleado_centros_delete_url"] = ""
        else:
            ctx["empleado_centros_add_url"] = reverse_lazy("tramites:empleado-centro-add")
            ctx["empleado_centros_delete_url"] = reverse_lazy("tramites:empleado-centro-delete")
        ctx["prefijos_oficio"] = list(models.PrefijoOficio.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["folio_prefijos"] = list(models.FolioPrefijo.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["prefijos_oficio_api_url"] = reverse_lazy("tramites_api:prefijo-oficio-list")
        ctx["tipos_violencia"] = list(models.TipoViolencia.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["tipos_violencia_api_url"] = reverse_lazy("tramites_api:tipo-violencia-list")
        ctx["solicitantes"] = list(models.Solicitante.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["solicitantes_api_url"] = reverse_lazy("tramites_api:solicitante-list")
        ctx["destinatarios"] = list(models.Destinatario.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["destinatarios_api_url"] = reverse_lazy("tramites_api:destinatario-list")
        return ctx


class CasoInternoFormMixin(CCTCatalogContextMixin):
    """Reutiliza el catálogo de CCT en formularios de trámites."""


class CasoInternoListView(LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    """Listado principal de trámites registrados."""

    permission_required = "licencias.view_casointerno"
    model = models.CasoInterno
    paginate_by = 20
    filterset_class = filters.CasoInternoFilter
    template_name = "tramites/tramites/tramites_list.html"
    context_object_name = "casos"
    ordering = "-fecha_registro"

    ORDERING_MAP = {
        "cct": "cct__cct",
        "tipo": "tipo_inicial__nombre",
        "expediente": "numero_oficio",
        "fecha": "fecha_apertura",
        "fecha_registro": "fecha_registro",
        "estatus": "estatus__nombre",
        "asesor": "asesor_cct",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "cct",
                "estatus",
                "tipo_inicial",
                "area_origen_inicial",
                "creado_por",
                "solicitante",
                "dirigido_a",
            )
            .prefetch_related("trabajadores_caso__trabajador", "centros_trabajo_adicionales")
        )

    def get_ordering(self):
        orden = (self.request.GET.get("orden") or "").strip()
        if not orden:
            return self.ordering
        descending = orden.startswith("-")
        key = orden.lstrip("-")
        field = self.ORDERING_MAP.get(key)
        if not field:
            return self.ordering
        return f"-{field}" if descending else field

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["folio_prefijos"] = list(models.FolioPrefijo.objects.filter(esta_activo=True).order_by("nombre"))
        buscar = (self.request.GET.get("buscar") or "").strip()
        metric = (self.request.GET.get("metric") or "").strip()
        tramite_tipo = (self.request.GET.get("tramite_tipo") or "").strip()
        tramite_estatus = (self.request.GET.get("tramite_estatus") or "").strip()
        ctx["buscar_q"] = buscar
        if buscar:
            tramites_query = (
                Q(numero_oficio__icontains=buscar)
                | Q(folios_generados__folio__icontains=buscar)
                | Q(asunto__icontains=buscar)
                | Q(generador_nombre__icontains=buscar)
                | Q(generador_iniciales__icontains=buscar)
                | Q(receptor_nombre__icontains=buscar)
                | Q(receptor_iniciales__icontains=buscar)
                | Q(generadores_adicionales__icontains=buscar)
                | Q(receptores_adicionales__icontains=buscar)
                | Q(tipo__nombre__icontains=buscar)
                | Q(estatus__nombre__icontains=buscar)
                | Q(caso__cct__cct__icontains=buscar)
                | Q(caso__cct_nombre__icontains=buscar)
                | Q(caso__folios_generados__folio__icontains=buscar)
                | Q(caso__descripcion_breve__icontains=buscar)
                | Q(caso__asunto__icontains=buscar)
                | Q(caso__generador_nombre__icontains=buscar)
                | Q(caso__generador_iniciales__icontains=buscar)
                | Q(caso__receptor_nombre__icontains=buscar)
                | Q(caso__receptor_iniciales__icontains=buscar)
                | Q(caso__generadores_adicionales__icontains=buscar)
                | Q(caso__receptores_adicionales__icontains=buscar)
                | Q(caso__trabajadores_manuales__icontains=buscar)
                | Q(caso__trabajadores__nombre__icontains=buscar)
                | Q(caso__trabajadores__rfc__icontains=buscar)
                | Q(caso__trabajadores__curp__icontains=buscar)
            )
            if buscar.isdigit():
                tramite_id = int(buscar)
                tramites_query |= Q(pk=tramite_id) | Q(caso__pk=tramite_id)
            tramites_qs = _tramites_list_base_queryset().filter(tramites_query).distinct().order_by("-fecha")
        else:
            tramites_qs = _tramites_list_base_queryset().order_by("-fecha")
        if tramite_tipo:
            tramite_tipo_filter = {"tipo_id": int(tramite_tipo)} if tramite_tipo.isdigit() else {"tipo__nombre__iexact": tramite_tipo}
            tramites_qs = _tramites_list_base_queryset().filter(**tramite_tipo_filter).order_by("-fecha")
        if tramite_estatus:
            tramite_estatus_filter = {"estatus_id": int(tramite_estatus)} if tramite_estatus.isdigit() else {"estatus__nombre__iexact": tramite_estatus}
            tramites_qs = _tramites_list_base_queryset().filter(**tramite_estatus_filter).order_by("-fecha")
        if metric in {"tramites-duplicados", "tramites-sin-expediente", "tramites-sn", "tramites-por-tipo", "tramites-por-estatus"}:
            sin_expediente_q = Q(numero_oficio="") | Q(numero_oficio__isnull=True)
            sn_expediente_q = Q(numero_oficio__iexact="S/N") | Q(numero_oficio__iexact="SN")
            tramites_base = _tramites_list_base_queryset()
            if metric == "tramites-sin-expediente":
                tramites_qs = tramites_base.filter(sin_expediente_q).order_by("-fecha")
            elif metric == "tramites-sn":
                tramites_qs = tramites_base.filter(sn_expediente_q).order_by("-fecha")
            elif metric == "tramites-por-tipo":
                tramites_qs = tramites_base.order_by("tipo__nombre", "-fecha")
            elif metric == "tramites-por-estatus":
                tramites_qs = tramites_base.order_by("estatus__nombre", "-fecha")
            else:
                dup_nums = list(
                    tramites_base.exclude(sin_expediente_q | sn_expediente_q)
                    .values("numero_oficio")
                    .annotate(total=Count("id"))
                    .filter(total__gt=1)
                    .values_list("numero_oficio", flat=True)
                )
                tramites_qs = tramites_base.filter(numero_oficio__in=dup_nums).order_by("-fecha")
        if getattr(self, "filterset", None) is not None:
            form = self.filterset.form
            if form.is_valid():
                fecha_apertura = form.cleaned_data.get("fecha_apertura")
                if fecha_apertura:
                    if fecha_apertura.start:
                        tramites_qs = tramites_qs.filter(caso__fecha_apertura__gte=fecha_apertura.start)
                    if fecha_apertura.stop:
                        tramites_qs = tramites_qs.filter(caso__fecha_apertura__lte=fecha_apertura.stop)
                fecha_registro = form.cleaned_data.get("fecha_registro")
                if fecha_registro:
                    if fecha_registro.start:
                        tramites_qs = tramites_qs.filter(caso__fecha_registro__gte=fecha_registro.start)
                    if fecha_registro.stop:
                        tramites_qs = tramites_qs.filter(caso__fecha_registro__lte=fecha_registro.stop)
        tramites_qs = _prefetch_tramite_creador(tramites_qs)
        tramites_paginator = Paginator(tramites_qs, 20)
        tramites_page_number = (self.request.GET.get("anexos_page") or "").strip() or 1
        tramites_page_obj = tramites_paginator.get_page(tramites_page_number)
        ctx["tramites_paginator"] = tramites_paginator
        ctx["tramites_page_obj"] = tramites_page_obj
        ctx["tramites_is_paginated"] = tramites_page_obj.has_other_pages()
        ctx["tramites_busqueda"] = list(tramites_page_obj.object_list)
        casos_listado = list(ctx.get("casos") or [])
        today = timezone.localdate()
        rule_index = sla.get_rule_index()
        casos_sla = sla.build_snapshots_for_casos(casos_listado, today=today, rule_index=rule_index)
        tramites_sla = sla.build_snapshots_for_tramites(
            ctx["tramites_busqueda"],
            today=today,
            rule_index=rule_index,
        )
        ctx["casos"] = casos_listado
        case_ids = {caso.pk for caso in casos_listado if caso.pk}
        case_ids.update({tramite.caso_id for tramite in ctx["tramites_busqueda"] if getattr(tramite, "caso_id", None)})
        case_tramites_counts: dict[int, int] = {}
        case_minutas_counts: dict[int, int] = {}
        if case_ids:
            case_tramites_counts = dict(
                models.TramiteCaso.objects.filter(caso_id__in=case_ids)
                .values("caso_id")
                .annotate(total=Count("id"))
                .values_list("caso_id", "total")
            )
            case_minutas_counts = dict(
                models.MinutaCaso.objects.filter(caso_id__in=case_ids)
                .values("caso_id")
                .annotate(total=Count("id"))
                .values_list("caso_id", "total")
            )
        tramite_ids = [tramite.pk for tramite in ctx["tramites_busqueda"] if getattr(tramite, "pk", None)]
        tramite_minutas_counts: dict[int, int] = {}
        if tramite_ids:
            tramite_minutas_counts = dict(
                models.MinutaTramite.objects.filter(tramite_id__in=tramite_ids)
                .values("tramite_id")
                .annotate(total=Count("id"))
                .values_list("tramite_id", "total")
            )
        trabajadores_por_caso: dict[int, str] = {}
        for caso in casos_listado:
            setattr(caso, "sla_snapshot", casos_sla.get(caso.pk, {}))
            tramites_anexos_count = case_tramites_counts.get(caso.pk, 0)
            minutas_adicionales_count = case_minutas_counts.get(caso.pk, 0)
            documentos_adjuntos_total = (1 if getattr(caso, "minuta", None) else 0) + minutas_adicionales_count
            setattr(caso, "tramites_anexos_count", tramites_anexos_count)
            setattr(caso, "documentos_adjuntos_total", documentos_adjuntos_total)
            setattr(caso, "tiene_documentos_adjuntos", documentos_adjuntos_total > 0)
            trabajador_listado = _build_trabajadores_listado(caso)
            setattr(caso, "trabajador_listado", trabajador_listado)
            setattr(caso, "solicitante_listado", _catalogo_nombre(caso.solicitante))
            setattr(caso, "dirigido_a_listado", _catalogo_nombre(caso.dirigido_a))
            generador_listado, generador_extra = _build_participante_listado(
                caso.generador_nombre,
                caso.generadores_adicionales,
            )
            receptor_listado, receptor_extra = _build_participante_listado(
                caso.receptor_nombre,
                caso.receptores_adicionales,
            )
            setattr(caso, "generador_listado", generador_listado)
            setattr(caso, "generador_extra_count", generador_extra)
            setattr(caso, "receptor_listado", receptor_listado)
            setattr(caso, "receptor_extra_count", receptor_extra)
            trabajadores_por_caso[caso.pk] = trabajador_listado
        for tramite in ctx["tramites_busqueda"]:
            setattr(tramite, "sla_snapshot", tramites_sla.get(tramite.pk, {}))
            caso = getattr(tramite, "caso", None)
            tramites_anexos_count = case_tramites_counts.get(getattr(tramite, "caso_id", None), 0)
            minutas_adicionales_count = tramite_minutas_counts.get(tramite.pk, 0)
            documentos_adjuntos_total = (1 if getattr(tramite, "minuta", None) else 0) + minutas_adicionales_count
            setattr(tramite, "tramites_anexos_count", tramites_anexos_count)
            setattr(tramite, "documentos_adjuntos_total", documentos_adjuntos_total)
            setattr(tramite, "tiene_documentos_adjuntos", documentos_adjuntos_total > 0)
            setattr(
                tramite,
                "solicitante_listado",
                _catalogo_nombre_fallback(getattr(tramite, "solicitante", None), getattr(caso, "solicitante", None)),
            )
            setattr(
                tramite,
                "dirigido_a_listado",
                _catalogo_nombre_fallback(getattr(tramite, "dirigido_a", None), getattr(caso, "dirigido_a", None)),
            )
            gen_listado, gen_extra = _build_participante_listado(
                getattr(tramite, "generador_nombre", ""),
                getattr(tramite, "generadores_adicionales", []),
            )
            rec_listado, rec_extra = _build_participante_listado(
                getattr(tramite, "receptor_nombre", ""),
                getattr(tramite, "receptores_adicionales", []),
            )
            setattr(tramite, "generador_listado", gen_listado)
            setattr(tramite, "generador_extra_count", gen_extra)
            setattr(tramite, "receptor_listado", rec_listado)
            setattr(tramite, "receptor_extra_count", rec_extra)
            if not caso:
                setattr(tramite, "trabajador_listado", "-")
                continue
            trabajador_listado = trabajadores_por_caso.get(caso.pk)
            if trabajador_listado is None:
                trabajador_listado = _build_trabajadores_listado(caso)
                trabajadores_por_caso[caso.pk] = trabajador_listado
            if trabajador_listado == "-":
                incidencia_tramite = str(tramite.incidencia_nombre_docente or "").strip()
                if incidencia_tramite:
                    trabajador_listado = incidencia_tramite
            setattr(caso, "trabajador_listado", trabajador_listado)
            setattr(tramite, "trabajador_listado", trabajador_listado)
        params = self.request.GET.copy()
        params.pop("orden", None)
        params.pop("page", None)
        base_qs = params.urlencode()
        ctx["orden_actual"] = self.request.GET.get("orden") or ""
        ctx["orden_base_qs"] = f"{base_qs}&" if base_qs else ""
        ctx["bulk_tramite_form"] = forms.BulkTramiteCasoForm(prefix="bulk_tramite")
        ctx["bulk_estatus_form"] = forms.BulkEstatusCasoForm()
        ctx["bulk_convertir_form"] = forms.ConvertirCasosAAnexoBulkForm()
        metric_labels = {
            "casos-sin-estatus": "Casos sin estatus",
            "casos-pendiente": "Casos con estatus Pendiente",
            "casos-con-folio": "Casos con folio",
            "casos-sin-folio": "Casos sin folio",
            "casos-duplicados": "Casos duplicados",
            "casos-sin-expediente": "Casos sin expediente",
            "casos-sn": "Casos con expediente S/N",
            "tramites-duplicados": "Trámites duplicados",
            "tramites-sin-expediente": "Trámites sin expediente",
            "tramites-sn": "Trámites con expediente S/N",
            "tramites-por-tipo": "Trámites por tipo",
            "tramites-por-estatus": "Trámites por estatus",
        }
        active_filters = []
        base_params = self.request.GET.copy()
        def _remove_param_url(param: str) -> str:
            params = base_params.copy()
            params.pop(param, None)
            return f"{reverse_lazy('tramites:casointerno-list')}?{params.urlencode()}" if params else reverse_lazy("tramites:casointerno-list")

        if buscar:
            active_filters.append({"label": "Buscar", "value": buscar, "remove_url": _remove_param_url("buscar")})
        if metric:
            active_filters.append({"label": "Métrica", "value": metric_labels.get(metric, metric), "remove_url": _remove_param_url("metric")})
        year = (self.request.GET.get("year") or "").strip()
        if year:
            active_filters.append({"label": "Año", "value": year, "remove_url": _remove_param_url("year")})
        show_ids = (self.request.GET.get("show_ids") or "1").strip()
        tipo_inicial = (self.request.GET.get("tipo_inicial") or "").strip()
        if tipo_inicial:
            tipo_label = tipo_inicial
            if tipo_inicial.isdigit():
                tipo_name = (
                    models.TipoProceso.objects.filter(pk=int(tipo_inicial)).values_list("nombre", flat=True).first()
                    or tipo_inicial
                )
                tipo_label = f"{tipo_name} ({tipo_inicial})" if show_ids == "1" else tipo_name
            active_filters.append({"label": "Tipo inicial", "value": tipo_label, "remove_url": _remove_param_url("tipo_inicial")})
        modalidad = (self.request.GET.get("modalidad") or "").strip()
        if modalidad:
            active_filters.append({"label": "Modalidad", "value": modalidad, "remove_url": _remove_param_url("modalidad")})
        violencia = (self.request.GET.get("violencia") or self.request.GET.get("tipo_violencia") or "").strip()
        if violencia:
            violencia_label = violencia
            if violencia.isdigit():
                violencia_name = (
                    models.TipoViolencia.objects.filter(pk=int(violencia)).values_list("nombre", flat=True).first()
                    or violencia
                )
                violencia_label = f"{violencia_name} ({violencia})" if show_ids == "1" else violencia_name
            active_filters.append({"label": "Tipo de violencia", "value": violencia_label, "remove_url": _remove_param_url("violencia")})
        gen_generador = (self.request.GET.get("generador_sexo") or "").strip()
        if gen_generador:
            active_filters.append({"label": "Género generador", "value": gen_generador, "remove_url": _remove_param_url("generador_sexo")})
        gen_receptor = (self.request.GET.get("receptor_sexo") or "").strip()
        if gen_receptor:
            active_filters.append({"label": "Género receptor", "value": gen_receptor, "remove_url": _remove_param_url("receptor_sexo")})
        asesor = (self.request.GET.get("asesor") or self.request.GET.get("asesor_cct") or "").strip()
        if asesor:
            active_filters.append({"label": "Asesor", "value": asesor, "remove_url": _remove_param_url("asesor")})
        cct = (self.request.GET.get("cct") or "").strip()
        if cct:
            cct_code = (
                models.PlantillaCentroTrabajo.objects.filter(cct__iexact=cct)
                .values_list("cct", flat=True)
                .first()
                or cct
            )
            cct_label = cct_code
            active_filters.append({"label": "CCT", "value": cct_label, "remove_url": _remove_param_url("cct")})
        tramite_tipo = (self.request.GET.get("tramite_tipo") or "").strip()
        if tramite_tipo:
            tramite_tipo_label = tramite_tipo
            if tramite_tipo.isdigit():
                tramite_tipo_name = (
                    models.TipoProceso.objects.filter(pk=int(tramite_tipo)).values_list("nombre", flat=True).first()
                    or tramite_tipo
                )
                tramite_tipo_label = f"{tramite_tipo_name} ({tramite_tipo})" if show_ids == "1" else tramite_tipo_name
            active_filters.append({"label": "Trámite tipo", "value": tramite_tipo_label, "remove_url": _remove_param_url("tramite_tipo")})
        tramite_estatus = (self.request.GET.get("tramite_estatus") or "").strip()
        if tramite_estatus:
            tramite_estatus_label = tramite_estatus
            if tramite_estatus.isdigit():
                tramite_estatus_name = (
                    models.EstatusTramite.objects.filter(pk=int(tramite_estatus)).values_list("nombre", flat=True).first()
                    or tramite_estatus
                )
                tramite_estatus_label = f"{tramite_estatus_name} ({tramite_estatus})" if show_ids == "1" else tramite_estatus_name
            active_filters.append({"label": "Trámite estatus", "value": tramite_estatus_label, "remove_url": _remove_param_url("tramite_estatus")})
        ctx["active_filters"] = active_filters
        ctx["clear_filters_url"] = reverse_lazy("tramites:casointerno-list")
        params = self.request.GET.copy()
        params["show_ids"] = "0"
        ctx["show_ids_disable_url"] = f"{reverse_lazy('tramites:casointerno-list')}?{params.urlencode()}"
        params["show_ids"] = "1"
        ctx["show_ids_enable_url"] = f"{reverse_lazy('tramites:casointerno-list')}?{params.urlencode()}"
        ctx["show_ids_enabled"] = show_ids == "1"
        saved_querystring = _build_saved_filter_querystring_from_request(
            self.request,
            allowed_keys=FILTROS_GUARDADOS_KEYS_CASOS,
        )
        filtros_guardados = list(
            models.FiltroGuardadoUsuario.objects.filter(
                usuario=self.request.user,
                alcance=models.FiltroGuardadoUsuario.ALCANCE_CASOS_LISTADO,
            ).order_by("nombre")
        )
        for filtro in filtros_guardados:
            query_string = _sanitize_saved_filter_querystring(
                filtro.query_string,
                allowed_keys=FILTROS_GUARDADOS_KEYS_CASOS,
            )
            filtro.apply_url = (
                f"{reverse_lazy('tramites:casointerno-list')}?{query_string}"
                if query_string
                else reverse_lazy("tramites:casointerno-list")
            )
        ctx["saved_filters_casos"] = filtros_guardados
        ctx["saved_filter_form_casos"] = forms.FiltroGuardadoOperacionForm(
            initial={
                "alcance": models.FiltroGuardadoUsuario.ALCANCE_CASOS_LISTADO,
                "querystring": saved_querystring,
            }
        )
        ctx["saved_filters_casos_querystring"] = saved_querystring
        return ctx


class CasoInternoBulkActionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.change_casointerno"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        action = request.POST.get("accion") or ""
        selected = request.POST.getlist("caso_ids")
        if not selected:
            messages.error(request, _("Selecciona al menos un caso."))
            return redirect(request.POST.get("next") or "tramites:casointerno-list")

        casos = models.CasoInterno.objects.filter(pk__in=selected).select_related("estatus")
        if action == "agregar_tramite":
            form = forms.BulkTramiteCasoForm(request.POST, request.FILES, prefix="bulk_tramite")
            if not form.is_valid():
                logger.warning(
                    "Bulk tramite invalid: errors=%s keys=%s files=%s",
                    form.errors.as_json(),
                    list(request.POST.keys()),
                    list(request.FILES.keys()),
                )
                messages.error(request, _("Completa los datos del trámite anexo."))
                return redirect(request.POST.get("next") or "tramites:casointerno-list")
            data = form.cleaned_data
            logger.info(
                "Bulk tramite OK: casos=%s data_keys=%s",
                len(casos),
                sorted(data.keys()),
            )
            minuta = data.get("minuta")
            minuta_bytes = None
            minuta_name = None
            if minuta:
                try:
                    minuta_bytes = minuta.read()
                    minuta_name = minuta.name
                finally:
                    try:
                        minuta.seek(0)
                    except Exception:
                        pass
            minutas = data.get("minutas") or []
            minutas_cache = []
            for archivo in minutas:
                try:
                    contenido = archivo.read()
                finally:
                    try:
                        archivo.seek(0)
                    except Exception:
                        pass
                minutas_cache.append((archivo.name, contenido))
            for caso in casos:
                tramite = models.TramiteCaso.objects.create(
                    caso=caso,
                    tipo=data["tipo"],
                    estatus=data.get("estatus"),
                    fecha=data["fecha"],
                    numero_oficio=data.get("numero_oficio") or "",
                    asunto=data.get("asunto") or "",
                    tipo_violencia=data.get("tipo_violencia"),
                    tipos_violencia_adicionales=data.get("tipos_violencia_adicionales") or [],
                    solicitante=data.get("solicitante"),
                    dirigido_a=data.get("dirigido_a"),
                    observaciones=data.get("observaciones") or "",
                    generador_nombre=data.get("generador_nombre") or "",
                    generador_iniciales=data.get("generador_iniciales") or "",
                    generador_sexo=data.get("generador_sexo") or "",
                    receptor_nombre=data.get("receptor_nombre") or "",
                    receptor_iniciales=data.get("receptor_iniciales") or "",
                    receptor_sexo=data.get("receptor_sexo") or "",
                    receptores_adicionales=data.get("receptores_adicionales") or [],
                    generadores_adicionales=data.get("generadores_adicionales") or [],
                    fecha_termino=data.get("fecha_termino"),
                    incidencia_nombre_docente=data.get("incidencia_nombre_docente") or "",
                    incidencia_afiliacion=data.get("incidencia_afiliacion") or "",
                    incidencia_fecha_inicio=data.get("incidencia_fecha_inicio"),
                    incidencia_fecha_termino=data.get("incidencia_fecha_termino"),
                    incidencia_dias_otorgados=data.get("incidencia_dias_otorgados"),
                    rangos_fechas_adicionales=data.get("rangos_fechas_adicionales") or [],
                )
                if minuta_bytes is not None and minuta_name:
                    tramite.minuta.save(minuta_name, ContentFile(minuta_bytes), save=True)
                for nombre, contenido in minutas_cache:
                    models.MinutaTramite.objects.create(
                        tramite=tramite,
                        archivo=ContentFile(contenido, name=nombre),
                    )
                registrar_cambio_estatus_tramite(
                    tramite=tramite,
                    usuario=request.user,
                    estatus_anterior=None,
                    estatus_nuevo=tramite.estatus,
                    comentario=data.get("comentario_estatus") or "",
                    notify=True,
                )
                inbox.notificar_tramite_creado(tramite, actor=request.user)
            messages.success(request, _("Trámite anexo agregado a los casos seleccionados."))
        elif action == "agregar_estatus":
            form = forms.BulkEstatusCasoForm(request.POST)
            if not form.is_valid():
                messages.error(request, _("Completa el estatus a aplicar."))
                return redirect(request.POST.get("next") or "tramites:casointerno-list")
            data = form.cleaned_data
            for caso in casos:
                registrar_cambio_estatus_caso(
                    caso=caso,
                    usuario=request.user,
                    estatus_anterior=caso.estatus,
                    estatus_nuevo=data["estatus_nuevo"],
                    comentario=data.get("comentario") or "",
                    notify=True,
                )
                caso.estatus = data["estatus_nuevo"]
                caso.save(update_fields=["estatus", "actualizado_en"])
            messages.success(request, _("Estatus actualizado en los casos seleccionados."))
        elif action == "convertir_anexo":
            form = forms.ConvertirCasosAAnexoBulkForm(request.POST, excluded_ids=selected)
            if not form.is_valid():
                messages.error(
                    request,
                    _("Completa los datos para convertir los casos: %s") % form.errors.as_text(),
                )
                return redirect(request.POST.get("next") or "tramites:casointerno-list")
            destino = form.cleaned_data["caso_destino"]
            mover_tramites = form.cleaned_data.get("mover_tramites_relacionados", True)
            eliminar_caso = form.cleaned_data.get("eliminar_caso_origen", True)
            motivo = (form.cleaned_data.get("motivo") or "").strip()
            convertidos = 0
            with transaction.atomic():
                for caso in casos:
                    if caso.pk == destino.pk:
                        continue
                    tramite = _crear_tramite_desde_caso(caso, target_case=destino)
                    models.BitacoraCaso.objects.create(
                        accion="convertir_anexo",
                        usuario=request.user if request.user.is_authenticated else None,
                        caso_origen=caso,
                        caso_destino=destino,
                        tramite=tramite,
                        detalle=(
                            f"Convertido a trámite anexo del caso {destino.pk}."
                            f"{' Motivo: ' + motivo if motivo else ''}"
                        ),
                    )
                    inbox.notificar_caso_convertido_a_anexo(
                        caso_origen=caso,
                        caso_destino=destino,
                        tramite=tramite,
                        actor=request.user,
                        motivo=motivo,
                    )
                    if mover_tramites:
                        caso.tramites_relacionados.update(caso=destino)
                    if eliminar_caso:
                        caso.delete()
                    convertidos += 1
            messages.success(
                request,
                _("Casos convertidos a trámites anexos: %(total)s.") % {"total": convertidos},
            )
        else:
            messages.error(request, _("Acción no válida."))
        return redirect(request.POST.get("next") or "tramites:casointerno-list")


class LicenciaRegistroListView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    """Listado de licencias registradas."""

    permission_required = "licencias.view_licenciaregistro"
    model = models.LicenciaRegistro
    paginate_by = 25
    filterset_class = filters.LicenciaRegistroFilter
    template_name = "tramites/licencias/licencias_list.html"
    context_object_name = "licencias"
    ordering = "-fecha_tramite"

    ORDERING_MAP = {
        "trabajador": "trabajador__nombre",
        "tipo": "tipo_tramite",
        "prorroga": "tipo_prorroga",
        "sindicato": "sindicato",
        "fecha": "fecha_tramite",
        "estatus": "estatus__nombre",
    }

    def get_queryset(self):
        return super().get_queryset().select_related("trabajador", "estatus")

    def get_ordering(self):
        orden = (self.request.GET.get("orden") or "").strip()
        if not orden:
            return self.ordering
        descending = orden.startswith("-")
        key = orden.lstrip("-")
        field = self.ORDERING_MAP.get(key)
        if not field:
            return self.ordering
        return f"-{field}" if descending else field

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("orden", None)
        params.pop("page", None)
        base_qs = params.urlencode()
        ctx["orden_actual"] = self.request.GET.get("orden") or ""
        ctx["orden_base_qs"] = f"{base_qs}&" if base_qs else ""
        return ctx


class LicenciaRegistroCreateView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Registro de una nueva licencia."""

    permission_required = "licencias.add_licenciaregistro"
    model = models.LicenciaRegistro
    form_class = forms.LicenciaRegistroForm
    template_name = "tramites/licencias/licencias_form.html"
    success_url = reverse_lazy("tramites:licencia-list")

    def form_valid(self, form) -> HttpResponse:
        form.instance.creado_por = self.request.user if self.request.user.is_authenticated else None
        response = super().form_valid(form)
        if self.object.estatus:
            registrar_cambio_estatus_licencia(
                licencia=self.object,
                usuario=self.request.user,
                estatus_anterior=None,
                estatus_nuevo=self.object.estatus,
            )
        messages.success(self.request, _("Licencia registrada correctamente."))
        return response

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["prefijos_oficio"] = list(models.PrefijoOficio.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["empleado_lookup_url"] = reverse_lazy("tramites:empleado-lookup")
        ctx["empleado_picker_url"] = reverse_lazy("tramites:empleado-picker")
        return ctx


class LicenciaRegistroUpdateView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Permite actualizar una licencia."""

    permission_required = "licencias.change_licenciaregistro"
    model = models.LicenciaRegistro
    form_class = forms.LicenciaRegistroForm
    template_name = "tramites/licencias/licencias_form.html"
    success_url = reverse_lazy("tramites:licencia-list")

    def form_valid(self, form) -> HttpResponse:
        old_status_id = (
            models.LicenciaRegistro.objects.filter(pk=self.object.pk)
            .values_list("estatus_id", flat=True)
            .first()
        )
        old_status = models.EstatusLicencia.objects.filter(pk=old_status_id).first()
        response = super().form_valid(form)
        if self.object.estatus and self.object.estatus != old_status:
            registrar_cambio_estatus_licencia(
                licencia=self.object,
                usuario=self.request.user,
                estatus_anterior=old_status,
                estatus_nuevo=self.object.estatus,
            )
        messages.success(self.request, _("Licencia actualizada."))
        return response

    def get_success_url(self):
        return self.request.GET.get("from_list") or str(self.success_url)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["prefijos_oficio"] = list(models.PrefijoOficio.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["empleado_lookup_url"] = reverse_lazy("tramites:empleado-lookup")
        ctx["empleado_picker_url"] = reverse_lazy("tramites:empleado-picker")
        return ctx


class LicenciaRegistroDetailView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalle de una licencia registrada."""

    permission_required = "licencias.view_licenciaregistro"
    model = models.LicenciaRegistro
    template_name = "tramites/licencias/licencias_detail.html"
    context_object_name = "licencia"

    def get_queryset(self):
        return super().get_queryset().select_related("trabajador", "estatus")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["historial_estatus"] = self.object.historial_estatus.select_related(
            "estatus_anterior", "estatus_nuevo", "usuario"
        ).order_by("-fecha_cambio", "-id")
        ctx["estatus_licencia_form"] = forms.HistorialEstatusLicenciaForm()
        return ctx


class LicenciaRegistroDeleteView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Elimina una licencia registrada."""

    permission_required = "licencias.delete_licenciaregistro"
    model = models.LicenciaRegistro
    template_name = "tramites/licencias/licencias_confirm_delete.html"
    success_url = reverse_lazy("tramites:licencia-list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        messages.success(request, _("Licencia eliminada."))
        return super().delete(request, *args, **kwargs)


class LicenciaEstatusCreateView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Agrega un cambio de estatus a una licencia y actualiza el estatus actual."""

    permission_required = "licencias.change_licenciaregistro"
    form_class = forms.HistorialEstatusLicenciaForm

    def dispatch(self, request, *args, **kwargs):
        self.licencia = get_object_or_404(
            models.LicenciaRegistro.objects.select_related("estatus"), pk=kwargs.get("pk")
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        nuevo_estatus = form.cleaned_data["estatus_nuevo"]
        comentario = form.cleaned_data.get("comentario", "")
        anterior = (
            self.licencia.historial_estatus.order_by("-fecha_cambio", "-id")
            .values_list("estatus_nuevo", flat=True)
            .first()
        )
        estatus_anterior_obj = None
        if anterior:
            try:
                estatus_anterior_obj = models.EstatusLicencia.objects.get(pk=anterior)
            except models.EstatusLicencia.DoesNotExist:
                estatus_anterior_obj = self.licencia.estatus
        else:
            estatus_anterior_obj = self.licencia.estatus
        registrar_cambio_estatus_licencia(
            licencia=self.licencia,
            usuario=self.request.user,
            estatus_anterior=estatus_anterior_obj,
            estatus_nuevo=nuevo_estatus,
            comentario=comentario,
        )
        self.licencia.estatus = nuevo_estatus
        self.licencia.save(update_fields=["estatus", "actualizado_en"])
        messages.success(self.request, _("Estatus de la licencia actualizado."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("tramites:licencia-detail", kwargs={"pk": self.licencia.pk})


class PlantillaEmpleadoListView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    """Listado de trabajadores registrados en plantilla."""

    permission_required = "licencias.view_plantillaempleado"
    model = models.PlantillaEmpleado
    paginate_by = 25
    filterset_class = filters.PlantillaEmpleadoFilter
    template_name = "tramites/licencias/empleados_list.html"
    context_object_name = "empleados"
    ordering = "nombre"


class PlantillaEmpleadoCreateView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Alta manual de trabajadores."""

    permission_required = "licencias.add_plantillaempleado"
    model = models.PlantillaEmpleado
    form_class = forms.PlantillaEmpleadoForm
    template_name = "tramites/licencias/empleados_form.html"
    success_url = reverse_lazy("tramites:empleado-list")

    def form_valid(self, form) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, _("Trabajador registrado correctamente."))
        return response


class PlantillaEmpleadoUpdateView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edición de trabajadores."""

    permission_required = "licencias.change_plantillaempleado"
    model = models.PlantillaEmpleado
    form_class = forms.PlantillaEmpleadoForm
    template_name = "tramites/licencias/empleados_form.html"
    success_url = reverse_lazy("tramites:empleado-list")

    def form_valid(self, form) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, _("Trabajador actualizado."))
        return response

    def get_success_url(self):
        return self.request.GET.get("from_list") or str(self.success_url)


class PlantillaEmpleadoDeleteView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Elimina un trabajador."""

    permission_required = "licencias.delete_plantillaempleado"
    model = models.PlantillaEmpleado
    template_name = "tramites/licencias/empleados_confirm_delete.html"
    success_url = reverse_lazy("tramites:empleado-list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        messages.success(request, _("Trabajador eliminado."))
        return super().delete(request, *args, **kwargs)


class TrabajadorLookupView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, View):
    """Endpoint para buscar trabajadores y obtener su último registro."""

    permission_required = "licencias.view_plantillaempleado"
    manage_permissions = (
        "licencias.add_plantillaempleado",
        "licencias.change_plantillaempleado",
        "licencias.add_casointerno",
        "licencias.change_casointerno",
        "licencias.add_tramitecaso",
        "licencias.change_tramitecaso",
    )

    def _can_manage_workers(self, request: HttpRequest) -> bool:
        return any(request.user.has_perm(perm) for perm in self.manage_permissions)

    def has_permission(self) -> bool:
        request = self.request
        return request.user.has_perm(self.permission_required) or self._can_manage_workers(request)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        empleado_id = request.GET.get("id")
        if empleado_id:
            empleado = get_object_or_404(models.PlantillaEmpleado, pk=empleado_id)
            info = get_latest_registro_info(empleado.id)
            sistema = ""
            if info.get("centros"):
                sistema = info["centros"][0].get("sistema") or ""
            data = {
                "id": empleado.id,
                "nombre": empleado.nombre,
                "correo": empleado.correo or "",
                "celular": empleado.celular or "",
                "sistema": sistema,
                "ultimo_ciclo": info.get("ultimo_ciclo") or "",
                "ultimo_anio": info.get("ultimo_anio"),
                "centros": info.get("centros", []),
                "registros": info.get("registros", []),
            }
            return JsonResponse(data)

        query = (request.GET.get("q") or "").strip()
        if not query:
            return JsonResponse({"results": []})
        qs = models.PlantillaEmpleado.objects.filter(
            dj_models.Q(nombre__icontains=query)
            | dj_models.Q(rfc__icontains=query)
            | dj_models.Q(curp__icontains=query)
        ).order_by("nombre")[:20]
        results = [
            {
                "id": empleado.id,
                "nombre": empleado.nombre,
                "rfc": empleado.rfc or "",
                "curp": empleado.curp or "",
            }
            for empleado in qs
        ]
        return JsonResponse({"results": results})

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        can_manage = self._can_manage_workers(request)
        if not can_manage:
            return JsonResponse(
                {"ok": False, "error": "No tienes permisos para registrar trabajadores."},
                status=403,
            )

        nombre = (request.POST.get("nombre") or "").strip()
        if not nombre:
            return JsonResponse({"ok": False, "error": "El nombre es obligatorio."}, status=400)

        rfc = (request.POST.get("rfc") or "").strip().upper() or None
        curp = (request.POST.get("curp") or "").strip().upper() or None
        empleado_id = (request.POST.get("id") or "").strip()

        empleado = None
        if empleado_id.isdigit():
            empleado = models.PlantillaEmpleado.objects.filter(pk=int(empleado_id)).first()
        if not empleado and rfc:
            empleado = models.PlantillaEmpleado.objects.filter(rfc__iexact=rfc).first()
        if not empleado and curp:
            empleado = models.PlantillaEmpleado.objects.filter(curp__iexact=curp).first()
        if not empleado:
            same_name = models.PlantillaEmpleado.objects.filter(nombre__iexact=nombre)
            if same_name.count() == 1:
                empleado = same_name.first()

        if empleado:
            update_fields = []
            if empleado.nombre != nombre:
                empleado.nombre = nombre
                update_fields.append("nombre")
            if rfc and (empleado.rfc or "").upper() != rfc:
                empleado.rfc = rfc
                update_fields.append("rfc")
            if curp and (empleado.curp or "").upper() != curp:
                empleado.curp = curp
                update_fields.append("curp")
            if update_fields:
                update_fields.append("actualizado_en")
                empleado.save(update_fields=update_fields)
        else:
            try:
                empleado = models.PlantillaEmpleado.objects.create(
                    nombre=nombre,
                    rfc=rfc,
                    curp=curp,
                )
            except IntegrityError:
                if rfc:
                    empleado = models.PlantillaEmpleado.objects.filter(rfc__iexact=rfc).first()
                if not empleado and curp:
                    empleado = models.PlantillaEmpleado.objects.filter(curp__iexact=curp).first()
                if not empleado:
                    return JsonResponse(
                        {
                            "ok": False,
                            "error": "No se pudo guardar el trabajador. Verifica RFC/CURP.",
                        },
                        status=400,
                    )

        clear_empleado_cache(empleado.id)
        return JsonResponse(
            {
                "ok": True,
                "id": empleado.id,
                "nombre": empleado.nombre,
                "rfc": empleado.rfc or "",
                "curp": empleado.curp or "",
            }
        )


class TrabajadorCentroAddView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, View):
    """Asocia un centro de trabajo al trabajador en el ciclo indicado."""

    permission_required = "licencias.add_plantillaregistro"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        empleado_id = (request.POST.get("empleado_id") or "").strip()
        cct = (request.POST.get("cct") or "").strip().upper()
        if not empleado_id or not cct:
            return JsonResponse({"ok": False, "error": "Datos incompletos."}, status=400)

        empleado = get_object_or_404(models.PlantillaEmpleado, pk=empleado_id)
        nombre = (request.POST.get("nombre") or "").strip()
        asesor = (request.POST.get("asesor") or "").strip()
        sostenimiento = normalise_sistema((request.POST.get("sostenimiento") or "").strip())
        subnivel = (request.POST.get("subnivel") or request.POST.get("servicio") or "").strip()
        municipio = (request.POST.get("municipio") or "").strip()
        turno = (request.POST.get("turno") or "").strip()

        centro, _ = models.PlantillaCentroTrabajo.objects.get_or_create(
            cct=cct,
            defaults={
                "nombre": nombre or "Sin nombre",
                "asesor": asesor,
                "sostenimiento": sostenimiento,
                "subnivel": subnivel,
                "municipio": municipio,
                "turno": turno,
            },
        )

        ciclo = (request.POST.get("ciclo") or "").strip()
        anio_raw = (request.POST.get("anio") or "").strip()
        anio = None
        if anio_raw.isdigit():
            anio = int(anio_raw)

        models.PlantillaRegistro.objects.get_or_create(
            empleado=empleado,
            centro_trabajo=centro,
            ciclo=ciclo,
            anio=anio,
            defaults={
                "situacion": "",
                "funcion": "",
                "grado_grupo_horas": "",
                "origen_id": None,
            },
        )

        clear_empleado_cache(empleado.id)
        info = get_latest_registro_info(empleado.id)
        return JsonResponse({"ok": True, **info})


class TrabajadorCentroDeleteView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, View):
    """Elimina una asociación de centro de trabajo del trabajador."""

    permission_required = "licencias.delete_plantillaregistro"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        registro_id = (request.POST.get("registro_id") or "").strip()
        empleado_id = (request.POST.get("empleado_id") or "").strip()
        cct = (request.POST.get("cct") or "").strip().upper()
        ciclo = (request.POST.get("ciclo") or "").strip()
        anio_raw = (request.POST.get("anio") or "").strip()

        if registro_id:
            registro = get_object_or_404(models.PlantillaRegistro, pk=registro_id)
            empleado_id = registro.empleado_id
            registro.delete()
        else:
            if not empleado_id or not cct:
                return JsonResponse({"ok": False, "error": "Datos incompletos."}, status=400)
            qs = models.PlantillaRegistro.objects.filter(
                empleado_id=empleado_id,
                centro_trabajo__cct__iexact=cct,
            )
            if ciclo:
                qs = qs.filter(ciclo=ciclo)
            if anio_raw.isdigit():
                qs = qs.filter(anio=int(anio_raw))
            qs.delete()

        clear_empleado_cache(int(empleado_id))
        info = get_latest_registro_info(int(empleado_id))
        return JsonResponse({"ok": True, **info})


class PlantillaEmpleadoPickerView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, View):
    """Modal para seleccionar trabajadores y rellenar la licencia."""

    permission_required = "licencias.view_plantillaempleado"
    template_name = "tramites/licencias/partials/empleados_picker.html"

    def _build_context(self, request: HttpRequest) -> Dict[str, Any]:
        query = (request.GET.get("q") or "").strip()
        readonly = (request.GET.get("readonly") or "").strip() == "1"
        qs = models.PlantillaEmpleado.objects.all()
        if query:
            qs = qs.filter(
                dj_models.Q(nombre__icontains=query)
                | dj_models.Q(rfc__icontains=query)
                | dj_models.Q(curp__icontains=query)
            )
        empleados = list(qs.order_by("nombre")[:25])
        return {
            "empleados": empleados,
            "query": query,
            "empleados_readonly": readonly,
        }

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(request, self.template_name, self._build_context(request))


class PlantillaEmpleadoPickerEditView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, View):
    """Edita trabajadores dentro del modal del picker."""

    permission_required = "licencias.change_plantillaempleado"
    template_name = "tramites/licencias/partials/empleados_edit.html"
    list_template_name = "tramites/licencias/partials/empleados_picker.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        empleado = get_object_or_404(models.PlantillaEmpleado, pk=kwargs.get("pk"))
        form = forms.PlantillaEmpleadoForm(instance=empleado)
        return render(request, self.template_name, {"form": form, "empleado": empleado})

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        empleado = get_object_or_404(models.PlantillaEmpleado, pk=kwargs.get("pk"))
        form = forms.PlantillaEmpleadoForm(request.POST, instance=empleado)
        if form.is_valid():
            form.save()
            messages.success(request, _("Trabajador actualizado."))
            picker = PlantillaEmpleadoPickerView()
            return render(request, self.list_template_name, picker._build_context(request))
        return render(request, self.template_name, {"form": form, "empleado": empleado})


class PlantillaEmpleadoPickerDeleteView(LicenciasFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, View):
    """Elimina trabajadores dentro del modal del picker."""

    permission_required = "licencias.delete_plantillaempleado"
    template_name = "tramites/licencias/partials/empleados_delete.html"
    list_template_name = "tramites/licencias/partials/empleados_picker.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        empleado = get_object_or_404(models.PlantillaEmpleado, pk=kwargs.get("pk"))
        return render(request, self.template_name, {"empleado": empleado})

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        empleado = get_object_or_404(models.PlantillaEmpleado, pk=kwargs.get("pk"))
        empleado.delete()
        messages.success(request, _("Trabajador eliminado."))
        picker = PlantillaEmpleadoPickerView()
        return render(request, self.list_template_name, picker._build_context(request))


class ReporteCasosListView(ReportesFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    """Módulo de reportes para filtrar casos y preparar impresión."""

    permission_required = "licencias.view_casointerno"
    model = models.CasoInterno
    paginate_by = 25
    filterset_class = filters.CasoInternoFilter
    template_name = "tramites/reportes/reportes_list.html"
    context_object_name = "casos"
    ordering = "-fecha_registro"

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("cct", "estatus", "tipo_inicial", "area_origen_inicial")
            .prefetch_related("trabajadores_caso__trabajador", "centros_trabajo_adicionales")
        )
        metric = (self.request.GET.get("metric") or "").strip()
        year = (self.request.GET.get("year") or "").strip()
        tipo_inicial = (self.request.GET.get("tipo_inicial") or "").strip()
        modalidad = (self.request.GET.get("modalidad") or "").strip()
        violencia = (self.request.GET.get("violencia") or self.request.GET.get("tipo_violencia") or "").strip()
        gen_generador = (self.request.GET.get("generador_sexo") or "").strip()
        gen_receptor = (self.request.GET.get("receptor_sexo") or "").strip()
        asesor = (self.request.GET.get("asesor") or self.request.GET.get("asesor_cct") or "").strip()
        cct = (self.request.GET.get("cct") or "").strip()
        sin_expediente_q = Q(numero_oficio="") | Q(numero_oficio__isnull=True)
        sn_expediente_q = Q(numero_oficio__iexact="S/N") | Q(numero_oficio__iexact="SN")
        if metric == "casos-sin-estatus":
            qs = qs.filter(estatus__isnull=True)
        elif metric == "casos-pendiente":
            qs = qs.filter(estatus__nombre__iexact="Pendiente")
        elif metric == "casos-con-folio":
            qs = qs.exclude(sin_expediente_q | sn_expediente_q)
        elif metric == "casos-sin-folio":
            qs = qs.filter(sin_expediente_q | sn_expediente_q)
        elif metric == "casos-sin-expediente":
            qs = qs.filter(sin_expediente_q)
        elif metric == "casos-sn":
            qs = qs.filter(sn_expediente_q)
        elif metric == "casos-duplicados":
            dup_nums = list(
                qs.exclude(sin_expediente_q | sn_expediente_q)
                .values("numero_oficio")
                .annotate(total=Count("id"))
                .filter(total__gt=1)
                .values_list("numero_oficio", flat=True)
            )
            qs = qs.filter(numero_oficio__in=dup_nums)
        if year.isdigit():
            qs = qs.filter(fecha_registro__year=int(year))
        if tipo_inicial:
            if tipo_inicial.isdigit():
                qs = qs.filter(tipo_inicial_id=int(tipo_inicial))
            else:
                qs = qs.filter(tipo_inicial__nombre__icontains=tipo_inicial)
        if modalidad:
            qs = qs.filter(cct_modalidad__iexact=modalidad)
        if violencia:
            if violencia.isdigit():
                qs = qs.filter(tipo_violencia_id=int(violencia))
            else:
                qs = qs.filter(tipo_violencia__nombre__iexact=violencia)
        if gen_generador:
            qs = qs.filter(generador_sexo=gen_generador)
        if gen_receptor:
            qs = qs.filter(receptor_sexo=gen_receptor)
        if asesor:
            qs = qs.filter(asesor_cct__icontains=asesor)
        if cct:
            qs = qs.filter(cct__cct__iexact=cct)
        return qs

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        for caso in ctx.get("casos", []):
            setattr(caso, "trabajador_listado", _build_trabajadores_listado(caso))
        return ctx


def _format_date(value) -> str:
    if not value:
        return ""
    return value.strftime("%Y-%m-%d")


def _format_datetime(value) -> str:
    if not value:
        return ""
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M:%S")


def _format_json(value) -> str:
    if not value:
        return ""
    try:
        return json.dumps(value, ensure_ascii=True)
    except TypeError:
        return str(value)


def _format_historial(entries) -> str:
    detalles = []
    for cambio in entries:
        detalles.append(
            "fecha_estatus={}; fecha_registro={}; anterior={}; nuevo={}; usuario={}; comentario={}".format(
                _format_date(getattr(cambio, "fecha_estatus_resuelta", None)),
                _format_datetime(cambio.fecha_cambio),
                getattr(cambio.estatus_anterior, "nombre", ""),
                getattr(cambio.estatus_nuevo, "nombre", ""),
                str(cambio.usuario) if cambio.usuario else "",
                cambio.comentario or "",
            )
        )
    return " || ".join(detalles)


def _format_incidencia(
    nombre: str,
    afiliacion: str,
    fecha_inicio,
    fecha_termino,
    dias_otorgados,
) -> str:
    partes = []
    if nombre:
        partes.append(nombre)
    if afiliacion:
        partes.append(afiliacion)
    if fecha_inicio:
        partes.append(_format_date(fecha_inicio))
    if fecha_termino:
        partes.append(_format_date(fecha_termino))
    if dias_otorgados:
        partes.append(f"{dias_otorgados} dias")
    return " | ".join(partes)


def _format_tramite(tramite: models.TramiteCaso) -> str:
    historial = _format_historial(tramite.historial_estatus.all())
    trabajador = "-"
    if getattr(tramite, "caso_id", None) and getattr(tramite, "caso", None):
        trabajador = _build_trabajadores_listado(tramite.caso)
    if trabajador == "-":
        incidencia_nombre = str(tramite.incidencia_nombre_docente or "").strip()
        if incidencia_nombre:
            trabajador = incidencia_nombre
    return " | ".join(
        [
            f"fecha={_format_date(tramite.fecha)}",
            f"tipo={getattr(tramite.tipo, 'nombre', '')}",
            f"estatus={getattr(tramite.estatus, 'nombre', '')}",
            f"expediente={tramite.numero_oficio or ''}",
            f"trabajador={trabajador}",
            f"asunto={tramite.asunto or ''}",
            f"solicitante={getattr(tramite.solicitante, 'nombre', '')}",
            f"dirigido_a={getattr(tramite.dirigido_a, 'nombre', '')}",
            f"tipo_violencia={getattr(tramite.tipo_violencia, 'nombre', '')}",
            f"tipos_violencia_adicionales={_format_json(tramite.tipos_violencia_adicionales)}",
            f"fecha_termino={_format_date(tramite.fecha_termino)}",
            f"generador={tramite.generador_nombre or ''}",
            f"generador_iniciales={tramite.generador_iniciales or ''}",
            f"generador_sexo={tramite.get_generador_sexo_display() if tramite.generador_sexo else ''}",
            f"receptor={tramite.receptor_nombre or ''}",
            f"receptor_iniciales={tramite.receptor_iniciales or ''}",
            f"receptor_sexo={tramite.get_receptor_sexo_display() if tramite.receptor_sexo else ''}",
            f"generadores_adicionales={_format_json(tramite.generadores_adicionales)}",
            f"receptores_adicionales={_format_json(tramite.receptores_adicionales)}",
            f"incidencia={_format_incidencia(tramite.incidencia_nombre_docente, tramite.get_incidencia_afiliacion_display() if tramite.incidencia_afiliacion else '', tramite.incidencia_fecha_inicio, tramite.incidencia_fecha_termino, tramite.incidencia_dias_otorgados)}",
            f"observaciones={tramite.observaciones or ''}",
            f"historial_estatus={historial}",
        ]
    )


def _reporte_ejecutivo_caso_queryset():
    historial_caso_qs = models.HistorialEstatusCaso.objects.select_related(
        "estatus_anterior",
        "estatus_nuevo",
        "usuario",
    ).order_by("fecha_cambio", "id")
    historial_tramite_qs = models.HistorialEstatusTramiteCaso.objects.select_related(
        "estatus_anterior",
        "estatus_nuevo",
        "usuario",
    ).order_by("fecha_cambio", "id")
    tramites_qs = (
        models.TramiteCaso.objects.select_related(
            "tipo",
            "estatus",
            "solicitante",
            "dirigido_a",
            "tipo_violencia",
        )
        .prefetch_related(
            "usuarios_involucrados",
            "minutas_adjuntas",
            Prefetch("historial_estatus", queryset=historial_tramite_qs),
        )
        .order_by("fecha", "id")
    )
    return (
        models.CasoInterno.objects.select_related(
            "cct",
            "estatus",
            "tipo_inicial",
            "area_origen_inicial",
            "solicitante",
            "dirigido_a",
            "tipo_violencia",
        )
        .prefetch_related(
            "usuarios_involucrados",
            "trabajadores_caso__trabajador",
            "centros_trabajo_adicionales",
            "minutas_adjuntas",
            Prefetch("historial_estatus", queryset=historial_caso_qs),
            Prefetch("tramites_relacionados", queryset=tramites_qs),
        )
        .order_by("-fecha_registro")
    )


def _build_reporte_caso_cronologia(
    caso: models.CasoInterno,
    historial_caso: list[models.HistorialEstatusCaso],
    tramites: list[models.TramiteCaso],
) -> list[dict[str, Any]]:
    eventos: list[dict[str, Any]] = []
    secuencia = 0

    def _registrar(
        *,
        orden: str,
        fecha,
        etapa: str,
        detalle: str,
        categoria: str,
        tramite_id: int | None = None,
    ) -> None:
        nonlocal secuencia
        if not orden:
            return
        eventos.append(
            {
                "orden": orden,
                "secuencia": secuencia,
                "fecha": fecha,
                "etapa": etapa,
                "detalle": detalle,
                "categoria": categoria,
                "tramite_id": tramite_id,
            }
        )
        secuencia += 1

    apertura = _format_date(caso.fecha_apertura)
    if apertura:
        _registrar(
            orden=f"{apertura} 00:00:00",
            fecha=caso.fecha_apertura,
            etapa="Apertura del caso",
            detalle=(
                f"Tipo inicial: {getattr(caso.tipo_inicial, 'nombre', 'Sin tipo inicial')}. "
                f"Estatus inicial: {getattr(caso.estatus, 'nombre', 'Sin estatus')}."
            ),
            categoria="caso",
        )

    for cambio in historial_caso:
        estatus_anterior = getattr(cambio.estatus_anterior, "nombre", "") or "Sin estatus previo"
        estatus_nuevo = getattr(cambio.estatus_nuevo, "nombre", "") or "Sin estatus"
        detalle = f"{estatus_anterior} -> {estatus_nuevo}"
        if cambio.comentario:
            detalle += f" · {cambio.comentario}"
        if cambio.usuario:
            detalle += f" (Registro: {cambio.usuario})"
        _registrar(
            orden=_format_datetime(cambio.fecha_cambio),
            fecha=cambio.fecha_cambio,
            etapa="Cambio de estatus del caso",
            detalle=detalle,
            categoria="estatus_caso",
        )

    for tramite in tramites:
        fecha_tramite = _format_date(tramite.fecha)
        _registrar(
            orden=f"{fecha_tramite} 00:00:00",
            fecha=tramite.fecha,
            etapa="Registro de tramite asociado",
            detalle=(
                f"Tramite #{tramite.pk} - {getattr(tramite.tipo, 'nombre', 'Sin tipo')} "
                f"({ 'Iniciador' if tramite.es_iniciador else 'Anexo' }) · "
                f"Estatus actual: {getattr(tramite.estatus, 'nombre', 'Sin estatus')}."
            ),
            categoria="tramite",
            tramite_id=tramite.pk,
        )
        for cambio in getattr(tramite, "historial_estatus_list", []):
            estatus_anterior = getattr(cambio.estatus_anterior, "nombre", "") or "Sin estatus previo"
            estatus_nuevo = getattr(cambio.estatus_nuevo, "nombre", "") or "Sin estatus"
            detalle = f"{estatus_anterior} -> {estatus_nuevo}"
            if cambio.comentario:
                detalle += f" · {cambio.comentario}"
            if cambio.usuario:
                detalle += f" (Registro: {cambio.usuario})"
            _registrar(
                orden=_format_datetime(cambio.fecha_cambio),
                fecha=cambio.fecha_cambio,
                etapa=f"Cambio de estatus del tramite #{tramite.pk}",
                detalle=detalle,
                categoria="estatus_tramite",
                tramite_id=tramite.pk,
            )

    eventos.sort(key=lambda item: (item["orden"], item["secuencia"]))
    return eventos


def _build_reporte_ejecutivo_context(
    caso: models.CasoInterno,
    *,
    tramite_foco: models.TramiteCaso | None = None,
) -> dict[str, Any]:
    historial_caso = list(caso.historial_estatus.all())
    tramites = list(caso.tramites_relacionados.all())
    usuarios_caso = list(caso.usuarios_involucrados.all())
    minutas_caso = list(caso.minutas_adjuntas.all())
    trabajador_listado = _build_trabajadores_listado(caso)

    for tramite in tramites:
        historial_tramite = list(tramite.historial_estatus.all())
        usuarios_tramite = list(tramite.usuarios_involucrados.all())
        minutas_tramite = list(tramite.minutas_adjuntas.all())
        setattr(tramite, "historial_estatus_list", historial_tramite)
        setattr(tramite, "usuarios_involucrados_list", usuarios_tramite)
        setattr(tramite, "minutas_adjuntas_list", minutas_tramite)

        trabajador_tramite = trabajador_listado
        if trabajador_tramite == "-":
            incidencia_tramite = str(tramite.incidencia_nombre_docente or "").strip()
            if incidencia_tramite:
                trabajador_tramite = incidencia_tramite
        setattr(tramite, "trabajador_listado", trabajador_tramite)

    tramite_foco_prefetched = None
    if tramite_foco:
        tramite_foco_prefetched = next(
            (tramite for tramite in tramites if tramite.pk == tramite_foco.pk),
            None,
        )
        if not tramite_foco_prefetched:
            tramite_foco_prefetched = tramite_foco
    cronologia = _build_reporte_caso_cronologia(caso, historial_caso, tramites)

    return {
        "historial_estatus_caso": historial_caso,
        "tramites_relacionados": tramites,
        "usuarios_caso": usuarios_caso,
        "minutas_caso": minutas_caso,
        "trabajadores_resumen": _build_trabajadores_resumen(caso),
        "trabajador_listado_caso": trabajador_listado,
        "cronologia_caso": cronologia,
        "reporte_generado_en": timezone.localtime(),
        "tramite_foco": tramite_foco_prefetched,
        "total_tramites_relacionados": len(tramites),
        "tramites_con_estatus": sum(1 for tramite in tramites if tramite.estatus_id),
    }


class CasoInternoReporteEjecutivoPrintView(
    ReportesFeatureFlagMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DetailView,
):
    """Reporte ejecutivo imprimible para un caso y sus tramites anexos."""

    permission_required = "licencias.view_casointerno"
    model = models.CasoInterno
    template_name = "tramites/reportes/reporte_ejecutivo_print.html"
    context_object_name = "caso"

    def get_queryset(self):
        return _reporte_ejecutivo_caso_queryset()

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.update(_build_reporte_ejecutivo_context(self.object))
        return ctx


class TramiteCasoReporteEjecutivoPrintView(
    ReportesFeatureFlagMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DetailView,
):
    """Reporte ejecutivo imprimible generado desde el resumen de un tramite anexo."""

    permission_required = "licencias.view_tramitecaso"
    model = models.TramiteCaso
    template_name = "tramites/reportes/reporte_ejecutivo_print.html"
    context_object_name = "tramite"

    def get_queryset(self):
        qs = super().get_queryset().select_related("caso", "tipo", "estatus")
        caso_pk = self.kwargs.get("caso_pk")
        if caso_pk:
            qs = qs.filter(caso_id=caso_pk)
        return qs

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        caso = _reporte_ejecutivo_caso_queryset().filter(pk=self.object.caso_id).first()
        if not caso:
            raise Http404("No se encontro el caso para generar el reporte ejecutivo.")
        ctx["caso"] = caso
        ctx.update(_build_reporte_ejecutivo_context(caso, tramite_foco=self.object))
        return ctx


class ReporteCasosPrintView(ReportesFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    """Vista imprimible con los casos filtrados."""

    permission_required = "licencias.view_casointerno"
    model = models.CasoInterno
    filterset_class = filters.CasoInternoFilter
    template_name = "tramites/reportes/reportes_print.html"
    context_object_name = "casos"
    ordering = "-fecha_registro"

    def get_queryset(self):
        historial_caso_qs = models.HistorialEstatusCaso.objects.select_related(
            "estatus_anterior",
            "estatus_nuevo",
            "usuario",
        ).order_by("fecha_cambio")
        historial_tramite_qs = models.HistorialEstatusTramiteCaso.objects.select_related(
            "estatus_anterior",
            "estatus_nuevo",
            "usuario",
        ).order_by("fecha_cambio")
        tramites_qs = (
            models.TramiteCaso.objects.select_related(
                "tipo",
                "estatus",
                "solicitante",
                "dirigido_a",
                "tipo_violencia",
            )
            .prefetch_related(Prefetch("historial_estatus", queryset=historial_tramite_qs))
            .order_by("fecha", "creado_en")
        )
        return (
            super()
            .get_queryset()
            .select_related(
                "cct",
                "estatus",
                "tipo_inicial",
                "area_origen_inicial",
                "solicitante",
                "dirigido_a",
                "tipo_violencia",
            )
            .prefetch_related(
                "trabajadores_caso__trabajador",
                "centros_trabajo_adicionales",
                Prefetch("historial_estatus", queryset=historial_caso_qs),
                Prefetch("tramites_relacionados", queryset=tramites_qs),
            )
        )

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        filterset = ctx.get("filter")
        has_filters = False
        if filterset and filterset.form.is_valid():
            for value in filterset.form.cleaned_data.values():
                if value not in (None, "", [], ()):
                    has_filters = True
                    break
        for caso in ctx.get("casos", []):
            trabajador_listado = _build_trabajadores_listado(caso)
            setattr(caso, "trabajador_listado", trabajador_listado)
            for tramite in caso.tramites_relacionados.all():
                trabajador_tramite = trabajador_listado
                if trabajador_tramite == "-":
                    incidencia_tramite = str(tramite.incidencia_nombre_docente or "").strip()
                    if incidencia_tramite:
                        trabajador_tramite = incidencia_tramite
                setattr(tramite, "trabajador_listado", trabajador_tramite)
        ctx["has_filters"] = has_filters
        return ctx


class ReporteCasosCsvView(ReportesFeatureFlagMixin, LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    """Exporta los casos filtrados en CSV para análisis externo."""

    permission_required = "licencias.view_casointerno"
    model = models.CasoInterno
    filterset_class = filters.CasoInternoFilter
    context_object_name = "casos"
    ordering = "-fecha_registro"

    def get_queryset(self):
        historial_caso_qs = models.HistorialEstatusCaso.objects.select_related(
            "estatus_anterior",
            "estatus_nuevo",
            "usuario",
        ).order_by("fecha_cambio")
        historial_tramite_qs = models.HistorialEstatusTramiteCaso.objects.select_related(
            "estatus_anterior",
            "estatus_nuevo",
            "usuario",
        ).order_by("fecha_cambio")
        tramites_qs = (
            models.TramiteCaso.objects.select_related(
                "tipo",
                "estatus",
                "solicitante",
                "dirigido_a",
                "tipo_violencia",
            )
            .prefetch_related(Prefetch("historial_estatus", queryset=historial_tramite_qs))
            .order_by("fecha", "creado_en")
        )
        return (
            super()
            .get_queryset()
            .select_related(
                "cct",
                "estatus",
                "tipo_inicial",
                "area_origen_inicial",
                "solicitante",
                "dirigido_a",
                "tipo_violencia",
                "creado_por",
            )
            .prefetch_related(
                "usuarios_involucrados",
                "trabajadores_caso__trabajador",
                "trabajadores",
                "centros_trabajo_adicionales",
                Prefetch("historial_estatus", queryset=historial_caso_qs),
                Prefetch("tramites_relacionados", queryset=tramites_qs),
            )
        )

    def render_to_response(self, context, **response_kwargs):
        casos = context.get("casos", [])
        timestamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
        response = HttpResponse(content_type="text/csv", **response_kwargs)
        response["Content-Disposition"] = (
            f'attachment; filename="reporte_tramites_{timestamp}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(
            [
                "caso_id",
                "cct",
                "cct_nombre",
                "cct_sistema",
                "cct_modalidad",
                "asesor_cct",
                "centros_adicionales_total",
                "centros_adicionales",
                "trabajador_principal",
                "trabajadores",
                "trabajadores_centros_ultimo_ciclo",
                "descripcion_breve",
                "fecha_apertura",
                "estatus",
                "tipo_inicial",
                "tipo_violencia",
                "tipos_violencia_adicionales",
                "numero_oficio",
                "folio_inicial",
                "solicitante",
                "dirigido_a",
                "generador_nombre",
                "generador_iniciales",
                "generador_sexo",
                "receptor_nombre",
                "receptor_iniciales",
                "receptor_sexo",
                "generadores_adicionales",
                "generadores_adicionales",
                "receptores_adicionales",
                "asunto",
                "area_origen_inicial",
                "fecha_oficio_inicial",
                "asunto_inicial",
                "observaciones_iniciales",
                "fecha_registro",
                "actualizado_en",
                "creado_por",
                "usuarios_involucrados",
                "fecha_termino",
                "incidencia_nombre_docente",
                "incidencia_afiliacion",
                "incidencia_fecha_inicio",
                "incidencia_fecha_termino",
                "incidencia_dias_otorgados",
                "historial_estatus_caso",
                "tramites_anexos_total",
                "tramites_anexos_detalle",
            ]
        )
        for caso in casos:
            historial_caso = _format_historial(caso.historial_estatus.all())
            tramites = [_format_tramite(tramite) for tramite in caso.tramites_relacionados.all()]
            usuarios = ", ".join(str(user) for user in caso.usuarios_involucrados.all())
            nombres_trabajadores, principal_nombre = _collect_trabajadores_nombres(caso)
            trabajadores_nombres = " | ".join(nombres_trabajadores)
            centros_ultimo = ""
            principal_rel = next(
                (rel for rel in caso.trabajadores_caso.all() if rel.es_principal and rel.trabajador_id),
                None,
            )
            if principal_rel and principal_rel.trabajador_id:
                info = get_latest_registro_info(principal_rel.trabajador_id)
                centros_ultimo = " | ".join(
                    f"{centro.get('cct','')} - {centro.get('nombre','')}"
                    for centro in info.get("centros", [])
                )
            centros_adicionales = list(caso.centros_trabajo_adicionales.all())
            centros_adicionales_str = " | ".join(
                f"{centro.cct} - {centro.nombre}" for centro in centros_adicionales
            )
            writer.writerow(
                [
                    caso.pk,
                    caso.cct_id,
                    caso.cct_nombre or "",
                    caso.cct_sistema or "",
                    caso.cct_modalidad or "",
                    caso.asesor_cct or "",
                    len(centros_adicionales),
                    centros_adicionales_str,
                    principal_nombre,
                    trabajadores_nombres,
                    centros_ultimo,
                    caso.descripcion_breve or "",
                    _format_date(caso.fecha_apertura),
                    getattr(caso.estatus, "nombre", ""),
                    getattr(caso.tipo_inicial, "nombre", ""),
                    getattr(caso.tipo_violencia, "nombre", ""),
                    _format_json(caso.tipos_violencia_adicionales),
                    caso.numero_oficio or "",
                    caso.folio_inicial or "",
                    getattr(caso.solicitante, "nombre", ""),
                    getattr(caso.dirigido_a, "nombre", ""),
                    caso.generador_nombre or "",
                    caso.generador_iniciales or "",
                    caso.get_generador_sexo_display() if caso.generador_sexo else "",
                    caso.receptor_nombre or "",
                    caso.receptor_iniciales or "",
                    caso.get_receptor_sexo_display() if caso.receptor_sexo else "",
                    _format_json(caso.generadores_adicionales),
                    _format_json(caso.receptores_adicionales),
                    caso.asunto or "",
                    getattr(caso.area_origen_inicial, "nombre", ""),
                    _format_date(caso.fecha_oficio_inicial),
                    caso.asunto_inicial or "",
                    caso.observaciones_iniciales or "",
                    _format_datetime(caso.fecha_registro),
                    _format_datetime(caso.actualizado_en),
                    str(caso.creado_por) if caso.creado_por else "",
                    usuarios,
                    _format_date(caso.fecha_termino),
                    caso.incidencia_nombre_docente or "",
                    caso.get_incidencia_afiliacion_display() if caso.incidencia_afiliacion else "",
                    _format_date(caso.incidencia_fecha_inicio),
                    _format_date(caso.incidencia_fecha_termino),
                    caso.incidencia_dias_otorgados or "",
                    historial_caso,
                    len(tramites),
                    " || ".join(tramites),
                ]
            )
        return response


class CasoInternoCreateView(
    CasoInternoFormMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    """Registro de un nuevo trámite."""

    permission_required = "licencias.add_casointerno"
    model = models.CasoInterno
    form_class = forms.CasoInternoForm
    template_name = "tramites/tramites/tramites_form.html"
    success_url = reverse_lazy("tramites:casointerno-list")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        form = ctx.get("form")
        if form:
            ctx["captura_guiada_config"] = _build_captura_guiada_context(
                form,
                ambito=captura_guiada.AMBITO_CASO,
            )
        return ctx

    def form_valid(self, form) -> HttpResponse:
        form.instance.creado_por = self.request.user if self.request.user.is_authenticated else None
        response = super().form_valid(form)
        form.save_trabajadores(self.object)
        form.save_centros_trabajo_adicionales(self.object)
        _asignar_folio_generado(
            folio_id=_get_folio_generado_id(self.request),
            caso=self.object,
        )
        if not self.object.usuarios_involucrados.exists():
            self.object.usuarios_involucrados.add(*_usuarios_involucrados_default(self.object))
        _guardar_minutas_caso(self.object, form.cleaned_data.get("minutas") or [])
        registrar_cambio_estatus_caso(
            caso=self.object,
            usuario=self.request.user,
            estatus_anterior=None,
            estatus_nuevo=self.object.estatus,
            notify=False,
        )
        notifications.notificar_caso_creado(self.object)
        inbox.notificar_caso_creado(self.object, actor=self.request.user)
        casos_dup, tramites_dup = _buscar_duplicados_expediente(
            form.cleaned_data.get("numero_oficio") or "",
            exclude_caso_id=self.object.pk,
        )
        _emitir_alerta_duplicados(
            self.request,
            titulo="Se detectaron expedientes duplicados:",
            casos=casos_dup,
            tramites=tramites_dup,
        )
        casos_part, tramites_part = _buscar_coincidencias_participantes(
            generador_nombre=form.cleaned_data.get("generador_nombre") or "",
            generador_iniciales=form.cleaned_data.get("generador_iniciales") or "",
            receptor_nombre=form.cleaned_data.get("receptor_nombre") or "",
            receptor_iniciales=form.cleaned_data.get("receptor_iniciales") or "",
            exclude_caso_id=self.object.pk,
        )
        _emitir_alerta_duplicados(
            self.request,
            titulo="Coincidencias por participantes (generadores/receptores):",
            casos=casos_part,
            tramites=tramites_part,
        )
        messages.success(self.request, _("Trámite registrado correctamente."))
        return response

    def form_invalid(self, form):
        folio_ids = _get_folios_preview_ids(self.request)
        _cancelar_folios_preview(
            folio_ids=folio_ids,
            usuario=self.request.user,
            detalle="Folio provisional cancelado: formulario de caso no guardado.",
        )
        return super().form_invalid(form)


class CasoInternoUpdateView(
    CasoInternoFormMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView
):
    """Permite actualizar los datos de un trámite."""

    permission_required = "licencias.change_casointerno"
    model = models.CasoInterno
    form_class = forms.CasoInternoForm
    template_name = "tramites/tramites/tramites_form.html"
    success_url = reverse_lazy("tramites:casointerno-list")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        form = ctx.get("form")
        if form:
            ctx["captura_guiada_config"] = _build_captura_guiada_context(
                form,
                ambito=captura_guiada.AMBITO_CASO,
            )
        return ctx

    def form_valid(self, form) -> HttpResponse:
        old_status_id = (
            models.CasoInterno.objects.filter(pk=self.object.pk)
            .values_list("estatus_id", flat=True)
            .first()
        )
        old_status = models.EstatusCaso.objects.filter(pk=old_status_id).first()
        response = super().form_valid(form)
        form.save_trabajadores(self.object)
        form.save_centros_trabajo_adicionales(self.object)
        _guardar_minutas_caso(self.object, form.cleaned_data.get("minutas") or [])
        if old_status != self.object.estatus:
            registrar_cambio_estatus_caso(
                caso=self.object,
                usuario=self.request.user,
                estatus_anterior=old_status,
                estatus_nuevo=self.object.estatus,
            )
        else:
            inbox.notificar_caso_actualizado(self.object, actor=self.request.user)
        casos_dup, tramites_dup = _buscar_duplicados_expediente(
            form.cleaned_data.get("numero_oficio") or "",
            exclude_caso_id=self.object.pk,
        )
        _emitir_alerta_duplicados(
            self.request,
            titulo="Se detectaron expedientes duplicados:",
            casos=casos_dup,
            tramites=tramites_dup,
        )
        casos_part, tramites_part = _buscar_coincidencias_participantes(
            generador_nombre=form.cleaned_data.get("generador_nombre") or "",
            generador_iniciales=form.cleaned_data.get("generador_iniciales") or "",
            receptor_nombre=form.cleaned_data.get("receptor_nombre") or "",
            receptor_iniciales=form.cleaned_data.get("receptor_iniciales") or "",
            exclude_caso_id=self.object.pk,
        )
        _emitir_alerta_duplicados(
            self.request,
            titulo="Coincidencias por participantes (generadores/receptores):",
            casos=casos_part,
            tramites=tramites_part,
        )
        messages.success(self.request, _("Trámite actualizado."))
        return response

    def get_success_url(self):
        return self.request.GET.get("from_list") or str(self.success_url)


class CasoInternoDetailView(
    CasoInternoFormMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView
):
    """Detalle de un trámite registrado."""

    permission_required = "licencias.view_casointerno"
    model = models.CasoInterno
    template_name = "tramites/tramites/tramites_detail.html"
    context_object_name = "caso"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "usuarios_involucrados",
                "trabajadores_caso__trabajador",
                "centros_trabajo_adicionales",
                Prefetch(
                    "comentarios_internos",
                    queryset=models.CasoComentarioInterno.objects.select_related("autor")
                    .prefetch_related("menciones")
                    .order_by("-creado_en", "-id"),
                    to_attr="comentarios_internos_prefetch",
                ),
                Prefetch(
                    "tareas_internas",
                    queryset=models.CasoTareaInterna.objects.select_related(
                        "responsable",
                        "creada_por",
                        "completada_por",
                    )
                    .annotate(
                        orden_estado=Case(
                            When(
                                estado=models.CasoTareaInterna.ESTADO_PENDIENTE,
                                then=Value(0),
                            ),
                            default=Value(1),
                            output_field=IntegerField(),
                        )
                    )
                    .order_by("orden_estado", "fecha_compromiso", "-creado_en"),
                    to_attr="tareas_internas_prefetch",
                ),
            )
        )

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.object = self.get_object()
        leidas = inbox.marcar_notificaciones_leidas(usuario=request.user, caso=self.object)
        if leidas:
            inbox.notificar_registro_leido(actor=request.user, caso=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        rule_index = sla.get_rule_index()
        ctx["caso_sla"] = sla.build_sla_snapshot_for_case(
            self.object,
            today=today,
            rule_index=rule_index,
        )
        ctx["historial_estatus"] = self.object.historial_estatus.select_related(
            "estatus_anterior", "estatus_nuevo", "usuario"
        ).order_by("-fecha_cambio", "-id")
        tramites_caso_qs = self.object.tramites_relacionados.select_related(
            "tipo",
            "estatus",
            "solicitante",
            "dirigido_a",
        ).order_by("-fecha", "-id")
        tramites_caso = list(_prefetch_tramite_creador(tramites_caso_qs))
        tramites_sla = sla.build_snapshots_for_tramites(
            tramites_caso,
            today=today,
            rule_index=rule_index,
        )
        tramite_ids = [tramite.pk for tramite in tramites_caso if getattr(tramite, "pk", None)]
        tramite_minutas_counts: dict[int, int] = {}
        if tramite_ids:
            tramite_minutas_counts = dict(
                models.MinutaTramite.objects.filter(tramite_id__in=tramite_ids)
                .values("tramite_id")
                .annotate(total=Count("id"))
                .values_list("tramite_id", "total")
            )
        tramites_anexos_count = len(tramites_caso)
        trabajador_listado = _build_trabajadores_listado(self.object)
        for tramite in tramites_caso:
            setattr(tramite, "sla_snapshot", tramites_sla.get(tramite.pk, {}))
            minutas_adicionales_count = tramite_minutas_counts.get(tramite.pk, 0)
            documentos_adjuntos_total = (1 if getattr(tramite, "minuta", None) else 0) + minutas_adicionales_count
            setattr(tramite, "tramites_anexos_count", tramites_anexos_count)
            setattr(tramite, "documentos_adjuntos_total", documentos_adjuntos_total)
            setattr(tramite, "tiene_documentos_adjuntos", documentos_adjuntos_total > 0)
            setattr(
                tramite,
                "solicitante_listado",
                _catalogo_nombre_fallback(getattr(tramite, "solicitante", None), getattr(self.object, "solicitante", None)),
            )
            setattr(
                tramite,
                "dirigido_a_listado",
                _catalogo_nombre_fallback(getattr(tramite, "dirigido_a", None), getattr(self.object, "dirigido_a", None)),
            )
            generador_listado, generador_extra = _build_participante_listado(
                getattr(tramite, "generador_nombre", ""),
                getattr(tramite, "generadores_adicionales", []),
            )
            receptor_listado, receptor_extra = _build_participante_listado(
                getattr(tramite, "receptor_nombre", ""),
                getattr(tramite, "receptores_adicionales", []),
            )
            setattr(tramite, "generador_listado", generador_listado)
            setattr(tramite, "generador_extra_count", generador_extra)
            setattr(tramite, "receptor_listado", receptor_listado)
            setattr(tramite, "receptor_extra_count", receptor_extra)
            trabajador_tramite = trabajador_listado
            if trabajador_tramite == "-":
                incidencia_tramite = str(tramite.incidencia_nombre_docente or "").strip()
                if incidencia_tramite:
                    trabajador_tramite = incidencia_tramite
            setattr(tramite, "trabajador_listado", trabajador_tramite)
        ctx["tramites_caso"] = tramites_caso
        ctx["minutas_adjuntas"] = self.object.minutas_adjuntas.all()
        ctx["tramite_caso_form"] = forms.TramiteCasoForm(prefix="tramite_caso", caso=self.object)
        ctx["estatus_tramite_form"] = forms.HistorialEstatusTramiteCasoForm()
        ctx["folio_prefijos"] = list(models.FolioPrefijo.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["estatus_caso_form"] = forms.HistorialEstatusCasoForm()
        ctx["convertir_caso_form"] = forms.ConvertirCasoAAnexoForm(caso_origen=self.object)
        ctx["tramite_iniciador"] = (
            self.object.tramites_relacionados.filter(es_iniciador=True).first()
        )
        ctx["prefijos_oficio"] = list(models.PrefijoOficio.objects.filter(esta_activo=True).order_by("nombre"))
        usuarios = list(self.object.usuarios_involucrados.all())
        usuario_filter = (self.request.GET.get("usuario") or "").strip()
        if usuario_filter:
            usuarios = [u for u in usuarios if str(u.pk) == usuario_filter]
        base_qs = models.BandejaNotificacionDestinatario.objects.filter(
            usuario__in=usuarios,
            notificacion__caso=self.object,
        )
        agg = (
            base_qs.values("usuario_id")
            .annotate(
                total=Count("id"),
                unread=Count("id", filter=Q(leido=False)),
                last_read=Max("leido_en"),
                last_sent=Max("notificacion__creado_en"),
            )
        )
        ultimos = (
            base_qs.select_related("notificacion")
            .order_by("usuario_id", "-notificacion__creado_en", "-id")
        )
        estado = {item["usuario_id"]: item for item in agg}
        ultimo_por_usuario = {}
        for item in ultimos:
            if item.usuario_id not in ultimo_por_usuario:
                ultimo_por_usuario[item.usuario_id] = item.notificacion
        ctx["usuarios_aviso_estado"] = [
            {
                "usuario": usuario,
                "total": estado.get(usuario.id, {}).get("total", 0),
                "unread": estado.get(usuario.id, {}).get("unread", 0),
                "last_read": estado.get(usuario.id, {}).get("last_read"),
                "last_sent": estado.get(usuario.id, {}).get("last_sent"),
                "last_title": getattr(ultimo_por_usuario.get(usuario.id), "titulo", ""),
                "last_message": getattr(ultimo_por_usuario.get(usuario.id), "mensaje", ""),
                "last_created": getattr(ultimo_por_usuario.get(usuario.id), "creado_en", None),
                "last_notificacion": ultimo_por_usuario.get(usuario.id),
            }
            for usuario in usuarios
        ]
        ctx["usuarios_involucrados_lista"] = list(self.object.usuarios_involucrados.all())
        comentarios_internos = list(getattr(self.object, "comentarios_internos_prefetch", []))
        tareas_internas = list(getattr(self.object, "tareas_internas_prefetch", []))
        ctx["comentarios_internos"] = comentarios_internos
        ctx["tareas_internas"] = tareas_internas
        ctx["tareas_internas_pendientes"] = sum(
            1 for tarea in tareas_internas if tarea.estado == models.CasoTareaInterna.ESTADO_PENDIENTE
        )
        ctx["comentario_interno_form"] = forms.CasoComentarioInternoForm(caso=self.object)
        ctx["tarea_interna_form"] = forms.CasoTareaInternaForm(caso=self.object)
        ctx["usuario_filtro"] = usuario_filter
        resumenes = _build_trabajadores_resumen(self.object)
        ctx["trabajadores_resumen"] = resumenes
        ctx["aviso_cct_mismatch"] = _build_aviso_cct_mismatch(self.object, resumenes)
        return ctx


class CasoTrabajadorSyncView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Sincroniza el CCT del caso con el último ciclo del trabajador principal."""

    permission_required = "licencias.change_casointerno"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("pk"))
        next_url = request.POST.get("next") or reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk})
        relacion = (
            caso.trabajadores_caso.select_related("centro_trabajo_preferido", "trabajador")
            .filter(es_principal=True)
            .first()
        )
        if not relacion:
            relacion = (
                caso.trabajadores_caso.select_related("centro_trabajo_preferido", "trabajador")
                .order_by("-creado_en")
                .first()
            )
        if not relacion:
            messages.error(request, _("No hay trabajadores vinculados para sincronizar."))
            return redirect(next_url)

        centro = relacion.centro_trabajo_preferido
        if not centro:
            info = get_latest_registro_info(relacion.trabajador_id)
            centros = info.get("centros") or []
            if centros:
                centro = (
                    models.PlantillaCentroTrabajo.objects.filter(
                        cct__iexact=centros[0].get("cct")
                    ).first()
                )
        if not centro:
            messages.error(request, _("No se encontró un centro de trabajo reciente para sincronizar."))
            return redirect(next_url)

        caso.cct = centro
        caso.cct_nombre = centro.nombre
        caso.cct_sistema = normalise_sistema(centro.sostenimiento)
        caso.cct_modalidad = centro.subnivel or ""
        if not caso.asesor_cct:
            caso.asesor_cct = centro.asesor or ""
        caso.save(
            update_fields=[
                "cct",
                "cct_nombre",
                "cct_sistema",
                "cct_modalidad",
                "asesor_cct",
                "actualizado_en",
            ]
        )
        if not relacion.centro_trabajo_preferido_id:
            relacion.centro_trabajo_preferido = centro
            relacion.save(update_fields=["centro_trabajo_preferido", "actualizado_en"])
        messages.success(request, _("Centro de trabajo sincronizado con el último ciclo."))
        return redirect(next_url)


class CasoInternoComentarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Crea un comentario interno ligado al expediente."""

    permission_required = "licencias.change_casointerno"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        caso = get_object_or_404(
            models.CasoInterno.objects.prefetch_related("usuarios_involucrados"),
            pk=kwargs.get("pk"),
        )
        fallback = reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk})
        next_url = _resolve_next_url(request, fallback=fallback)
        form = forms.CasoComentarioInternoForm(request.POST, caso=caso)
        if not form.is_valid():
            messages.error(
                request,
                _("No fue posible registrar el comentario interno: %s") % form.errors.as_text(),
            )
            return redirect(next_url)

        with transaction.atomic():
            comentario = form.save(caso=caso, autor=request.user)
            menciones = list(comentario.menciones.filter(is_active=True))
            auditoria.registrar_cambio_critico(
                modulo="caso",
                accion="creado",
                descripcion=f"Comentario interno agregado · Caso {caso.pk}",
                despues={
                    "mensaje": comentario.mensaje,
                    "menciones": sorted(user.pk for user in menciones),
                },
                metadata={
                    "tipo": "comentario_interno",
                    "comentario_id": comentario.pk,
                    "menciones": sorted(user.pk for user in menciones),
                },
                actor=request.user,
                instancia=comentario,
                caso_id=caso.pk,
            )
        if menciones:
            inbox.notificar_caso_mencion(
                comentario=comentario,
                usuarios=menciones,
                actor=request.user,
            )
        messages.success(request, _("Comentario interno registrado."))
        return redirect(next_url)


class CasoInternoTareaCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Crea una tarea/acuerdo interno para el expediente."""

    permission_required = "licencias.change_casointerno"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        caso = get_object_or_404(
            models.CasoInterno.objects.prefetch_related("usuarios_involucrados"),
            pk=kwargs.get("pk"),
        )
        fallback = reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk})
        next_url = _resolve_next_url(request, fallback=fallback)
        form = forms.CasoTareaInternaForm(request.POST, caso=caso)
        if not form.is_valid():
            messages.error(
                request,
                _("No fue posible registrar la tarea interna: %s") % form.errors.as_text(),
            )
            return redirect(next_url)

        with transaction.atomic():
            tarea = form.save(caso=caso, creador=request.user)
            auditoria.registrar_cambio_critico(
                modulo="caso",
                accion="creado",
                descripcion=f"Tarea interna creada · Caso {caso.pk}",
                despues={
                    "titulo": tarea.titulo,
                    "descripcion": tarea.descripcion,
                    "responsable_id": tarea.responsable_id,
                    "fecha_compromiso": tarea.fecha_compromiso.isoformat(),
                    "estado": tarea.estado,
                },
                metadata={
                    "tipo": "tarea_interna",
                    "tarea_id": tarea.pk,
                },
                actor=request.user,
                instancia=tarea,
                caso_id=caso.pk,
            )
        inbox.notificar_caso_tarea_asignada(tarea, actor=request.user)
        messages.success(request, _("Tarea interna registrada."))
        return redirect(next_url)


class CasoInternoTareaCompletarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Marca una tarea interna como completada con auditoría."""

    permission_required = "licencias.change_casointerno"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        tarea = get_object_or_404(
            models.CasoTareaInterna.objects.select_related(
                "caso",
                "responsable",
                "creada_por",
                "completada_por",
            ),
            pk=kwargs.get("tarea_pk"),
            caso_id=kwargs.get("pk"),
        )
        fallback = reverse("tramites:casointerno-detail", kwargs={"pk": tarea.caso_id})
        next_url = _resolve_next_url(request, fallback=fallback)
        antes = {
            "estado": tarea.estado,
            "completada_en": tarea.completada_en.isoformat() if tarea.completada_en else None,
            "completada_por_id": tarea.completada_por_id,
        }
        changed = tarea.marcar_completada(usuario=request.user)
        if not changed:
            messages.info(request, _("La tarea ya se encontraba completada."))
            return redirect(next_url)
        despues = {
            "estado": tarea.estado,
            "completada_en": tarea.completada_en.isoformat() if tarea.completada_en else None,
            "completada_por_id": tarea.completada_por_id,
        }
        auditoria.registrar_cambio_critico(
            modulo="caso",
            accion="actualizado",
            descripcion=f"Tarea interna completada · Caso {tarea.caso_id}",
            antes=antes,
            despues=despues,
            metadata={
                "tipo": "tarea_interna",
                "tarea_id": tarea.pk,
                "accion_tarea": "completar",
            },
            actor=request.user,
            instancia=tarea,
            caso_id=tarea.caso_id,
        )
        inbox.notificar_caso_tarea_completada(tarea, actor=request.user)
        messages.success(request, _("Tarea marcada como completada."))
        return redirect(next_url)


class TramiteCasoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Permite agregar trámites adicionales a un caso."""

    permission_required = "licencias.add_tramitecaso"
    model = models.TramiteCaso
    form_class = forms.TramiteCasoForm
    template_name = "tramites/tramites/tramite_caso_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("caso_pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["prefix"] = "tramite_caso"
        kwargs["caso"] = self.caso
        return kwargs

    def form_valid(self, form):
        form.instance.caso = self.caso
        response = super().form_valid(form)
        if _tramite_post_has_worker_payload(form, self.request.POST):
            form.save_trabajadores(self.caso)
        _asignar_folio_generado(
            folio_id=_get_folio_generado_id(self.request, form.prefix or None),
            tramite=self.object,
        )
        _guardar_minutas_tramite(self.object, form.cleaned_data.get("minutas") or [])
        if self.object.estatus_id:
            registrar_cambio_estatus_tramite(
                tramite=self.object,
                usuario=self.request.user,
                estatus_anterior=None,
                estatus_nuevo=self.object.estatus,
                comentario=self.request.POST.get("comentario_estatus", ""),
                notify=False,
            )
        notifications.notificar_tramite_caso_creado(self.object)
        inbox.notificar_tramite_creado(self.object, actor=self.request.user)
        casos_dup, tramites_dup = _buscar_duplicados_expediente(
            form.cleaned_data.get("numero_oficio") or "",
            exclude_tramite_id=self.object.pk,
        )
        _emitir_alerta_duplicados(
            self.request,
            titulo="Se detectaron expedientes duplicados:",
            casos=casos_dup,
            tramites=tramites_dup,
        )
        casos_part, tramites_part = _buscar_coincidencias_participantes(
            generador_nombre=form.cleaned_data.get("generador_nombre") or "",
            generador_iniciales=form.cleaned_data.get("generador_iniciales") or "",
            receptor_nombre=form.cleaned_data.get("receptor_nombre") or "",
            receptor_iniciales=form.cleaned_data.get("receptor_iniciales") or "",
            exclude_tramite_id=self.object.pk,
        )
        _emitir_alerta_duplicados(
            self.request,
            titulo="Coincidencias por participantes (generadores/receptores):",
            casos=casos_part,
            tramites=tramites_part,
        )
        messages.success(self.request, _("Trámite agregado al caso."))
        return response

    def form_invalid(self, form):
        folio_ids = _get_folios_preview_ids(self.request, form.prefix or None)
        _cancelar_folios_preview(
            folio_ids=folio_ids,
            usuario=self.request.user,
            detalle="Folio provisional cancelado: formulario de trámite anexo no guardado.",
        )
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("tramites:casointerno-detail", kwargs={"pk": self.caso.pk})

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["caso"] = self.caso
        form = ctx.get("form")
        if form:
            ctx["captura_guiada_config"] = _build_captura_guiada_context(
                form,
                ambito=captura_guiada.AMBITO_TRAMITE,
            )
        ctx["prefijos_oficio"] = list(models.PrefijoOficio.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["trabajadores_resumen"] = _build_trabajadores_resumen(self.caso)
        ctx["cct_lookup_url"] = reverse_lazy("tramites:cct-lookup")
        ctx["cct_api_url"] = reverse_lazy("tramites_api:cct-list")
        ctx["empleado_lookup_url"] = reverse_lazy("tramites:empleado-lookup")
        ensure_cct_catalog_loaded()
        catalogo = list(
            models.PlantillaCentroTrabajo.objects.order_by("cct").values(
                "cct", "nombre", "subnivel", "asesor", "sostenimiento"
            )
        )
        for item in catalogo:
            item["sostenimiento"] = normalise_sistema(item.get("sostenimiento"))
            item["servicio"] = item.pop("subnivel", "") or ""
        ctx["cct_catalogo"] = catalogo
        return ctx


class TramiteCasoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalle de un trámite asociado a un caso."""

    permission_required = "licencias.view_tramitecaso"
    model = models.TramiteCaso
    template_name = "tramites/tramites/tramite_caso_detail.html"
    context_object_name = "tramite"

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("caso", "tipo", "estatus", "solicitante", "dirigido_a", "tipo_violencia")
            .prefetch_related(
                "usuarios_involucrados",
                "caso__usuarios_involucrados",
                "caso__trabajadores_caso__trabajador",
                "caso__centros_trabajo_adicionales",
            )
        )
        caso_pk = self.kwargs.get("caso_pk")
        if caso_pk:
            qs = qs.filter(caso_id=caso_pk)
        return qs

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.object = self.get_object()
        leidas = inbox.marcar_notificaciones_leidas(usuario=request.user, tramite=self.object)
        if leidas:
            inbox.notificar_registro_leido(actor=request.user, tramite=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        rule_index = sla.get_rule_index()
        ctx["tramite_sla"] = sla.build_sla_snapshot_for_tramite(
            self.object,
            today=today,
            rule_index=rule_index,
        )
        ctx["historial_estatus"] = self.object.historial_estatus.select_related(
            "estatus_anterior", "estatus_nuevo", "usuario"
        ).order_by("-fecha_cambio", "-id")
        ctx["minutas_adjuntas"] = self.object.minutas_adjuntas.all()
        ctx["estatus_tramite_form"] = forms.HistorialEstatusTramiteCasoForm()
        ctx["promover_tramite_form"] = forms.PromoverTramiteACasoForm(tramite=self.object)
        ctx["folio_prefijos"] = list(models.FolioPrefijo.objects.filter(esta_activo=True).order_by("nombre"))
        usuarios = list(self.object.usuarios_involucrados.all())
        if not usuarios:
            usuarios = list(self.object.caso.usuarios_involucrados.all())
        usuario_filter = (self.request.GET.get("usuario") or "").strip()
        if usuario_filter:
            usuarios = [u for u in usuarios if str(u.pk) == usuario_filter]
        base_qs = models.BandejaNotificacionDestinatario.objects.filter(
            usuario__in=usuarios,
            notificacion__tramite=self.object,
        )
        agg = (
            base_qs.values("usuario_id")
            .annotate(
                total=Count("id"),
                unread=Count("id", filter=Q(leido=False)),
                last_read=Max("leido_en"),
                last_sent=Max("notificacion__creado_en"),
            )
        )
        ultimos = (
            base_qs.select_related("notificacion")
            .order_by("usuario_id", "-notificacion__creado_en", "-id")
        )
        estado = {item["usuario_id"]: item for item in agg}
        ultimo_por_usuario = {}
        for item in ultimos:
            if item.usuario_id not in ultimo_por_usuario:
                ultimo_por_usuario[item.usuario_id] = item.notificacion
        ctx["usuarios_aviso_estado"] = [
            {
                "usuario": usuario,
                "total": estado.get(usuario.id, {}).get("total", 0),
                "unread": estado.get(usuario.id, {}).get("unread", 0),
                "last_read": estado.get(usuario.id, {}).get("last_read"),
                "last_sent": estado.get(usuario.id, {}).get("last_sent"),
                "last_title": getattr(ultimo_por_usuario.get(usuario.id), "titulo", ""),
                "last_message": getattr(ultimo_por_usuario.get(usuario.id), "mensaje", ""),
                "last_created": getattr(ultimo_por_usuario.get(usuario.id), "creado_en", None),
                "last_notificacion": ultimo_por_usuario.get(usuario.id),
            }
            for usuario in usuarios
        ]
        ctx["usuarios_involucrados_lista"] = list(
            self.object.usuarios_involucrados.all() or self.object.caso.usuarios_involucrados.all()
        )
        ctx["usuario_filtro"] = usuario_filter
        ctx["trabajadores_resumen"] = _build_trabajadores_resumen(self.object.caso)
        return ctx


class TramiteCasoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Permite editar un trámite asociado a un caso."""

    permission_required = "licencias.change_tramitecaso"
    model = models.TramiteCaso
    form_class = forms.TramiteCasoForm
    template_name = "tramites/tramites/tramite_caso_form.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("caso")
        caso_pk = self.kwargs.get("caso_pk")
        if caso_pk:
            qs = qs.filter(caso_id=caso_pk)
        return qs

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["prefix"] = "tramite_caso"
        kwargs["caso"] = getattr(self.object, "caso", None)
        return kwargs

    def form_valid(self, form):
        old_status_id = (
            models.TramiteCaso.objects.filter(pk=self.object.pk)
            .values_list("estatus_id", flat=True)
            .first()
        )
        old_status = models.EstatusTramite.objects.filter(pk=old_status_id).first()
        response = super().form_valid(form)
        if _tramite_post_has_worker_payload(form, self.request.POST):
            form.save_trabajadores(self.object.caso)
        _guardar_minutas_tramite(self.object, form.cleaned_data.get("minutas") or [])
        if old_status != self.object.estatus:
            registrar_cambio_estatus_tramite(
                tramite=self.object,
                usuario=self.request.user,
                estatus_anterior=old_status,
                estatus_nuevo=self.object.estatus,
                comentario=self.request.POST.get("comentario_estatus", ""),
            )
        else:
            inbox.notificar_tramite_actualizado(self.object, actor=self.request.user)
        casos_dup, tramites_dup = _buscar_duplicados_expediente(
            form.cleaned_data.get("numero_oficio") or "",
            exclude_tramite_id=self.object.pk,
        )
        _emitir_alerta_duplicados(
            self.request,
            titulo="Se detectaron expedientes duplicados:",
            casos=casos_dup,
            tramites=tramites_dup,
        )
        casos_part, tramites_part = _buscar_coincidencias_participantes(
            generador_nombre=form.cleaned_data.get("generador_nombre") or "",
            generador_iniciales=form.cleaned_data.get("generador_iniciales") or "",
            receptor_nombre=form.cleaned_data.get("receptor_nombre") or "",
            receptor_iniciales=form.cleaned_data.get("receptor_iniciales") or "",
            exclude_tramite_id=self.object.pk,
        )
        _emitir_alerta_duplicados(
            self.request,
            titulo="Coincidencias por participantes (generadores/receptores):",
            casos=casos_part,
            tramites=tramites_part,
        )
        messages.success(self.request, _("Trámite actualizado."))
        return response

    def get_success_url(self):
        return reverse_lazy(
            "tramites:tramite-caso-detail",
            kwargs={"caso_pk": self.object.caso_id, "pk": self.object.pk},
        )

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["caso"] = self.object.caso
        form = ctx.get("form")
        if form:
            ctx["captura_guiada_config"] = _build_captura_guiada_context(
                form,
                ambito=captura_guiada.AMBITO_TRAMITE,
            )
        ctx["prefijos_oficio"] = list(models.PrefijoOficio.objects.filter(esta_activo=True).order_by("nombre"))
        ctx["trabajadores_resumen"] = _build_trabajadores_resumen(self.object.caso)
        ctx["cct_lookup_url"] = reverse_lazy("tramites:cct-lookup")
        ctx["cct_api_url"] = reverse_lazy("tramites_api:cct-list")
        ctx["empleado_lookup_url"] = reverse_lazy("tramites:empleado-lookup")
        ensure_cct_catalog_loaded()
        catalogo = list(
            models.PlantillaCentroTrabajo.objects.order_by("cct").values(
                "cct", "nombre", "subnivel", "asesor", "sostenimiento"
            )
        )
        for item in catalogo:
            item["sostenimiento"] = normalise_sistema(item.get("sostenimiento"))
            item["servicio"] = item.pop("subnivel", "") or ""
        ctx["cct_catalogo"] = catalogo
        return ctx


class TramiteCasoDefinirIniciadorView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Marca un trámite asociado como el iniciador del caso."""

    permission_required = "licencias.change_tramitecaso"

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("caso_pk"))
        tramite = get_object_or_404(models.TramiteCaso, pk=kwargs.get("tramite_pk"), caso=caso)
        with transaction.atomic():
            models.TramiteCaso.objects.filter(caso=caso, es_iniciador=True).update(es_iniciador=False)
            tramite.es_iniciador = True
            tramite.save(update_fields=["es_iniciador"])
            caso.tipo_inicial = tramite.tipo
            caso.fecha_apertura = tramite.fecha
            caso.save(update_fields=["tipo_inicial", "fecha_apertura", "actualizado_en"])
        messages.success(request, _("Trámite marcado como iniciador del caso."))
        return redirect(reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk}))


class TramiteCasoQuitarIniciadorView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Quita la marca de iniciador a un trámite asociado."""

    permission_required = "licencias.change_tramitecaso"

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("caso_pk"))
        tramite = get_object_or_404(models.TramiteCaso, pk=kwargs.get("tramite_pk"), caso=caso)
        if not tramite.es_iniciador:
            messages.info(request, _("El trámite no está marcado como iniciador."))
            return redirect(reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk}))
        with transaction.atomic():
            tramite.es_iniciador = False
            tramite.save(update_fields=["es_iniciador"])
        messages.success(request, _("Trámite desmarcado como iniciador."))
        return redirect(reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk}))


class CasoInternoConvertirAAnexoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Convierte un caso en trámite anexo de otro caso."""

    permission_required = "licencias.change_casointerno"

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("pk"))
        form = forms.ConvertirCasoAAnexoForm(request.POST, caso_origen=caso)
        if not form.is_valid():
            messages.error(request, _("Completa los datos para convertir el caso."))
            return redirect(reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk}))
        destino = form.cleaned_data["caso_destino"]
        mover_tramites = form.cleaned_data.get("mover_tramites_relacionados", True)
        eliminar_caso = form.cleaned_data.get("eliminar_caso_origen", True)
        motivo = (form.cleaned_data.get("motivo") or "").strip()
        with transaction.atomic():
            tramite = _crear_tramite_desde_caso(caso, target_case=destino)
            models.BitacoraCaso.objects.create(
                accion="convertir_anexo",
                usuario=request.user if request.user.is_authenticated else None,
                caso_origen=caso,
                caso_destino=destino,
                tramite=tramite,
                detalle=(
                    f"Convertido a trámite anexo del caso {destino.pk}."
                    f"{' Motivo: ' + motivo if motivo else ''}"
                ),
            )
            inbox.notificar_caso_convertido_a_anexo(
                caso_origen=caso,
                caso_destino=destino,
                tramite=tramite,
                actor=request.user,
                motivo=motivo,
            )
            if mover_tramites:
                caso.tramites_relacionados.update(caso=destino)
            if eliminar_caso:
                caso.delete()
        messages.success(request, _("Caso convertido en trámite anexo."))
        return redirect(reverse("tramites:casointerno-detail", kwargs={"pk": destino.pk}))


class TramiteCasoPromoverACasoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Convierte un trámite anexo en el nuevo caso base."""

    permission_required = "licencias.change_tramitecaso"

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        tramite = get_object_or_404(
            models.TramiteCaso,
            pk=kwargs.get("pk"),
            caso_id=kwargs.get("caso_pk"),
        )
        form = forms.PromoverTramiteACasoForm(request.POST, tramite=tramite)
        if not form.is_valid():
            messages.error(request, _("Completa los datos para promover el trámite."))
            return redirect(
                reverse(
                    "tramites:tramite-caso-detail",
                    kwargs={"caso_pk": tramite.caso_id, "pk": tramite.pk},
                )
            )
        old_case = tramite.caso
        with transaction.atomic():
            nuevo_caso = _crear_caso_desde_tramite(
                tramite,
                estatus=form.cleaned_data["estatus_caso"],
                tipo_inicial=form.cleaned_data["tipo_inicial"],
                fecha_apertura=form.cleaned_data["fecha_apertura"],
            )
            if form.cleaned_data.get("mover_tramites_relacionados", True):
                old_case.tramites_relacionados.exclude(pk=tramite.pk).update(caso=nuevo_caso)
            if form.cleaned_data.get("mover_caso_actual_a_anexo", True):
                _crear_tramite_desde_caso(old_case, target_case=nuevo_caso)
            tramite.delete()
            if form.cleaned_data.get("eliminar_caso_anterior", True):
                old_case.delete()
        messages.success(request, _("Trámite promovido a caso base."))
        return redirect(reverse("tramites:casointerno-detail", kwargs={"pk": nuevo_caso.pk}))


class FolioRegistroListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "licencias.view_folioregistro"
    model = models.FolioRegistro
    template_name = "tramites/folios/folios_list.html"
    context_object_name = "folios"
    ordering = "-creado_en"
    paginate_by = 25
    session_prefijo_key = "folios_prefijo_activo"

    def get_queryset(self):
        qs = super().get_queryset().order_by("-creado_en").prefetch_related("casos", "tramite")
        prefijo = (self.request.GET.get("prefijo") or "").strip()
        estado = (self.request.GET.get("estado") or "").strip().lower()
        if "prefijo" in self.request.GET:
            if prefijo:
                self.request.session[self.session_prefijo_key] = prefijo
            else:
                self.request.session.pop(self.session_prefijo_key, None)
        else:
            prefijo = (self.request.session.get(self.session_prefijo_key) or "").strip()
        if prefijo:
            qs = qs.filter(prefijo=prefijo)
        if estado == "activos":
            qs = qs.filter(activo=True)
        elif estado == "inactivos":
            qs = qs.filter(activo=False)
        return qs

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()
        prefijo = (self.request.GET.get("prefijo") or "").strip()
        estado = (self.request.GET.get("estado") or "").strip().lower()
        if "prefijo" not in self.request.GET:
            prefijo = (self.request.session.get(self.session_prefijo_key) or "").strip()
        ctx["q"] = q
        ctx["prefijo_seleccionado"] = prefijo
        ctx["estado_seleccionado"] = estado or "todos"
        folio_prefijos = list(models.FolioPrefijo.objects.filter(esta_activo=True).order_by("nombre"))
        prefijo_counts = (
            models.FolioRegistro.objects.values("prefijo").annotate(total=Count("id")).order_by()
        )
        prefijo_counts_map = {item["prefijo"]: item["total"] for item in prefijo_counts}
        for prefijo_item in folio_prefijos:
            prefijo_item.contador = prefijo_counts_map.get(prefijo_item.nombre, 0)
        ctx["folio_prefijos"] = folio_prefijos
        qs_params = {}
        if q:
            qs_params["q"] = q
        if prefijo:
            qs_params["prefijo"] = prefijo
        if estado:
            qs_params["estado"] = estado
        ctx["folios_query"] = urllib.parse.urlencode(qs_params)
        folios = list(ctx.get("folios") or [])
        if folios:
            folio_numbers = [folio.folio for folio in folios if folio.folio]
            casos_por_folio: dict[str, dict[int, models.CasoInterno]] = {}
            tramites_por_folio: dict[str, dict[int, models.TramiteCaso]] = {}

            def add_caso(folio_text: str, caso: models.CasoInterno | None) -> None:
                if not folio_text or not caso:
                    return
                casos_por_folio.setdefault(folio_text, {})[caso.pk] = caso

            def add_tramite(folio_text: str, tramite: models.TramiteCaso | None) -> None:
                if not folio_text or not tramite:
                    return
                tramites_por_folio.setdefault(folio_text, {})[tramite.pk] = tramite

            for folio in folios:
                for caso in folio.casos.all():
                    add_caso(folio.folio, caso)
                if folio.tramite and folio.tramite.caso_id:
                    add_caso(folio.folio, folio.tramite.caso)
                if folio.tramite:
                    add_tramite(folio.folio, folio.tramite)

            if folio_numbers:
                for caso in models.CasoInterno.objects.filter(
                    numero_oficio__in=folio_numbers
                ).only("id", "numero_oficio"):
                    add_caso(caso.numero_oficio, caso)
                for tramite in models.TramiteCaso.objects.filter(
                    numero_oficio__in=folio_numbers
                ).select_related("caso", "tipo"):
                    if tramite.caso_id:
                        add_caso(tramite.numero_oficio, tramite.caso)
                    add_tramite(tramite.numero_oficio, tramite)

            for folio in folios:
                folio.casos_relacionados = list(
                    casos_por_folio.get(folio.folio, {}).values()
                )
                folio.tramites_asociados = list(
                    tramites_por_folio.get(folio.folio, {}).values()
                )
        casos = []
        tramites = []
        if q:
            casos = (
                models.CasoInterno.objects.filter(
                    Q(cct__cct__icontains=q)
                    | Q(cct__nombre__icontains=q)
                    | Q(cct_nombre__icontains=q)
                    | Q(numero_oficio__icontains=q)
                    | Q(descripcion_breve__icontains=q)
                    | Q(asunto__icontains=q)
                    | Q(generador_nombre__icontains=q)
                    | Q(generador_iniciales__icontains=q)
                    | Q(receptor_nombre__icontains=q)
                    | Q(receptor_iniciales__icontains=q)
                )
                .order_by("-fecha_apertura")[:25]
            )
            tramites = (
                models.TramiteCaso.objects.select_related("caso", "tipo", "caso__cct")
                .filter(
                    Q(numero_oficio__icontains=q)
                    | Q(asunto__icontains=q)
                    | Q(generador_nombre__icontains=q)
                    | Q(generador_iniciales__icontains=q)
                    | Q(receptor_nombre__icontains=q)
                    | Q(receptor_iniciales__icontains=q)
                    | Q(caso__cct__cct__icontains=q)
                    | Q(caso__cct__nombre__icontains=q)
                )
                .order_by("-fecha")[:25]
            )
        ctx["casos_resultados"] = casos
        ctx["tramites_resultados"] = tramites
        return ctx


class FolioRegistroDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "licencias.view_folioregistro"
    model = models.FolioRegistro
    template_name = "tramites/folios/folios_detail.html"
    context_object_name = "folio"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("casos", "tramite", "actividades__usuario")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["actividades"] = self.object.actividades.select_related("usuario")
        casos_map: dict[int, models.CasoInterno] = {
            caso.pk: caso for caso in self.object.casos.all()
        }
        tramites_map: dict[int, models.TramiteCaso] = {}
        if self.object.tramite and self.object.tramite.caso_id:
            casos_map[self.object.tramite.caso_id] = self.object.tramite.caso
            tramites_map[self.object.tramite.pk] = self.object.tramite
        if self.object.folio:
            for caso in models.CasoInterno.objects.filter(
                numero_oficio=self.object.folio
            ).only("id", "numero_oficio"):
                casos_map[caso.pk] = caso
            for tramite in models.TramiteCaso.objects.filter(
                numero_oficio=self.object.folio
            ).select_related("caso", "tipo"):
                if tramite.caso_id:
                    casos_map[tramite.caso_id] = tramite.caso
                tramites_map[tramite.pk] = tramite
        ctx["casos_asociados"] = list(casos_map.values())
        ctx["tramites_asociados"] = list(tramites_map.values())
        return ctx


class FolioRegistroCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "licencias.add_folioregistro"
    model = models.FolioRegistro
    form_class = forms.FolioRegistroForm
    template_name = "tramites/folios/folios_form.html"
    success_url = reverse_lazy("tramites:folio-list")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["folio_prefijos"] = list(models.FolioPrefijo.objects.filter(esta_activo=True).order_by("nombre"))
        return ctx

    def form_valid(self, form):
        prefijo_obj = form.cleaned_data["prefijo"]
        tipo = form.cleaned_data["tipo"]
        casos = list(form.cleaned_data.get("casos") or [])
        tramite = form.cleaned_data.get("tramite")
        registro = _generar_folio(
            usuario=self.request.user,
            tipo=tipo,
            casos=casos,
            tramite=tramite,
            prefijo=(prefijo_obj.nombre if prefijo_obj else FOLIO_PREFIJO_DEFAULT),
        )
        if form.cleaned_data.get("notas"):
            registro.notas = form.cleaned_data["notas"]
            registro.save(update_fields=["notas"])
        if casos:
            for caso in casos:
                if caso.numero_oficio != registro.folio:
                    caso.numero_oficio = registro.folio
                    caso.save(update_fields=["numero_oficio", "actualizado_en"])
        if tramite:
            tramite.numero_oficio = registro.folio
            tramite.save(update_fields=["numero_oficio", "actualizado_en"])
        messages.success(self.request, _("Folio generado correctamente."))
        return redirect(self.success_url)


class FolioRegistroUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "licencias.change_folioregistro"
    model = models.FolioRegistro
    form_class = forms.FolioRegistroForm
    template_name = "tramites/folios/folios_form.html"
    success_url = reverse_lazy("tramites:folio-list")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["folio_prefijos"] = list(models.FolioPrefijo.objects.filter(esta_activo=True).order_by("nombre"))
        return ctx

    def form_valid(self, form):
        prev_casos = set(self.object.casos.values_list("pk", flat=True))
        prev_tramite_id = self.object.tramite_id
        prev_folio = self.object.folio
        response = super().form_valid(form)
        new_casos = set(self.object.casos.values_list("pk", flat=True))
        new_tramite_id = self.object.tramite_id

        removed_ids = prev_casos - new_casos
        if removed_ids:
            for caso in models.CasoInterno.objects.filter(pk__in=removed_ids):
                if caso.numero_oficio == prev_folio:
                    if not caso.folios_generados.exclude(pk=self.object.pk).exists():
                        caso.numero_oficio = ""
                        caso.save(update_fields=["numero_oficio", "actualizado_en"])

        if new_casos:
            for caso in models.CasoInterno.objects.filter(pk__in=new_casos):
                if caso.numero_oficio != self.object.folio:
                    caso.numero_oficio = self.object.folio
                    caso.save(update_fields=["numero_oficio", "actualizado_en"])

        if prev_tramite_id and prev_tramite_id != new_tramite_id:
            prev_tramite = models.TramiteCaso.objects.filter(pk=prev_tramite_id).first()
            if prev_tramite and prev_tramite.numero_oficio == prev_folio:
                prev_tramite.numero_oficio = ""
                prev_tramite.save(update_fields=["numero_oficio", "actualizado_en"])

        if self.object.tramite_id:
            tramite = self.object.tramite
            if tramite and tramite.numero_oficio != self.object.folio:
                tramite.numero_oficio = self.object.folio
                tramite.save(update_fields=["numero_oficio", "actualizado_en"])

        if new_casos:
            count = len(new_casos)
            messages.success(
                self.request,
                _(f"Folio actualizado y asociado a {count} caso(s)."),
            )
        elif self.object.tramite_id:
            messages.success(
                self.request,
                _(f"Folio actualizado y asociado al Trámite #{self.object.tramite_id}."),
            )
        else:
            messages.success(self.request, _("Folio actualizado correctamente."))

        models.FolioActividad.objects.create(
            folio=self.object,
            accion="editado",
            usuario=self.request.user,
            detalle="Edición de folio",
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, _("No se pudo guardar el folio. Revisa los campos marcados."))
        return super().form_invalid(form)


class FolioRegistroDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "licencias.delete_folioregistro"
    model = models.FolioRegistro
    template_name = "tramites/folios/folios_confirm_delete.html"
    success_url = reverse_lazy("tramites:folio-list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        folio_texto = self.object.folio
        for caso in self.object.casos.all():
            if caso.numero_oficio == folio_texto:
                caso.numero_oficio = ""
                caso.save(update_fields=["numero_oficio", "actualizado_en"])
        if self.object.tramite and self.object.tramite.numero_oficio == folio_texto:
            self.object.tramite.numero_oficio = ""
            self.object.tramite.save(update_fields=["numero_oficio", "actualizado_en"])
        self.object.activo = False
        self.object.eliminado_en = timezone.now()
        self.object.eliminado_por = request.user
        self.object.save(update_fields=["activo", "eliminado_en", "eliminado_por"])
        models.FolioActividad.objects.create(
            folio=self.object,
            accion="eliminado",
            usuario=request.user,
            detalle="Folio desactivado",
        )
        messages.success(request, _("Folio desactivado."))
        return redirect(self.success_url)


class FolioRegistroReactivarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.change_folioregistro"

    def post(self, request, *args, **kwargs):
        folio = get_object_or_404(models.FolioRegistro, pk=kwargs["pk"])
        if folio.activo:
            messages.info(request, _("El folio ya está activo."))
            return redirect(reverse("tramites:folio-list"))
        folio.activo = True
        folio.eliminado_en = None
        folio.eliminado_por = None
        folio.save(update_fields=["activo", "eliminado_en", "eliminado_por"])
        models.FolioActividad.objects.create(
            folio=folio,
            accion="editado",
            usuario=request.user,
            detalle="Folio reactivado",
        )
        messages.success(request, _("Folio reactivado."))
        return redirect(reverse("tramites:folio-list"))


class FolioGenerarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.add_folioregistro"

    def post(self, request, *args, **kwargs):
        tipo = request.POST.get("tipo")
        prefijo_id = request.POST.get("prefijo_id")
        if not prefijo_id:
            messages.error(request, _("Selecciona un prefijo."))
            return redirect(request.POST.get("next") or "tramites:folio-list")
        prefijo = get_object_or_404(models.FolioPrefijo, pk=prefijo_id)
        caso = None
        tramite = None
        if tipo == "caso":
            caso_id = request.POST.get("caso_id")
            caso = get_object_or_404(models.CasoInterno, pk=caso_id)
            if caso.numero_oficio:
                messages.warning(request, _("El caso ya tiene número de expediente."))
                return redirect(request.POST.get("next") or "tramites:casointerno-detail")
        elif tipo == "tramite":
            tramite_id = request.POST.get("tramite_id")
            tramite = get_object_or_404(models.TramiteCaso, pk=tramite_id)
            if tramite.numero_oficio:
                messages.warning(request, _("El trámite ya tiene número de expediente."))
                return redirect(request.POST.get("next") or "tramites:tramite-caso-detail")
        else:
            messages.error(request, _("Tipo inválido."))
            return redirect(request.POST.get("next") or "tramites:folio-list")

        registro = _generar_folio(
            usuario=request.user,
            tipo=tipo,
            casos=[caso] if caso else None,
            tramite=tramite,
            prefijo=prefijo.nombre,
        )
        if caso:
            caso.numero_oficio = registro.folio
            caso.save(update_fields=["numero_oficio", "actualizado_en"])
            return redirect(request.POST.get("next") or reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk}))
        if tramite:
            tramite.numero_oficio = registro.folio
            tramite.save(update_fields=["numero_oficio", "actualizado_en"])
            return redirect(
                request.POST.get("next")
                or reverse("tramites:tramite-caso-detail", kwargs={"caso_pk": tramite.caso_id, "pk": tramite.pk})
            )
        return redirect(request.POST.get("next") or "tramites:folio-list")


class FolioGenerarPreviewView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.add_folioregistro"

    def post(self, request, *args, **kwargs):
        prefijo_id = request.POST.get("prefijo_id")
        tipo = request.POST.get("tipo")
        if not prefijo_id or not tipo:
            return JsonResponse({"error": "Datos incompletos."}, status=400)
        if tipo not in ("caso", "tramite"):
            return JsonResponse({"error": "Tipo inválido."}, status=400)
        prefijo = get_object_or_404(models.FolioPrefijo, pk=prefijo_id)
        registro = _generar_folio(
            usuario=request.user,
            tipo=tipo,
            prefijo=prefijo.nombre,
        )
        return JsonResponse({"folio": registro.folio, "folio_id": registro.pk})


class FolioGenerarCancelarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.add_folioregistro"

    def post(self, request, *args, **kwargs):
        folio_ids = _get_folios_preview_ids(request)
        cancelados = _cancelar_folios_preview(
            folio_ids=folio_ids,
            usuario=request.user,
            detalle="Folio provisional cancelado: formulario abandonado sin guardar.",
        )
        return JsonResponse({"cancelados": cancelados, "ids": folio_ids})


class FolioBuscarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.view_folioregistro"

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        q = (request.GET.get("q") or "").strip()
        casos = []
        tramites = []
        if q:
            is_numeric = q.isdigit()
            casos = (
                models.CasoInterno.objects.filter(
                    Q(cct__cct__icontains=q)
                    | Q(cct_nombre__icontains=q)
                    | Q(numero_oficio__icontains=q)
                    | Q(descripcion_breve__icontains=q)
                    | Q(asunto__icontains=q)
                    | Q(generador_nombre__icontains=q)
                    | Q(generador_iniciales__icontains=q)
                    | Q(receptor_nombre__icontains=q)
                    | Q(receptor_iniciales__icontains=q)
                    | (Q(pk=int(q)) if is_numeric else Q())
                )
                .order_by("-fecha_apertura")[:25]
            )
            tramites = (
                models.TramiteCaso.objects.select_related("caso", "tipo", "caso__cct")
                .filter(
                    Q(numero_oficio__icontains=q)
                    | Q(asunto__icontains=q)
                    | Q(generador_nombre__icontains=q)
                    | Q(generador_iniciales__icontains=q)
                    | Q(receptor_nombre__icontains=q)
                    | Q(receptor_iniciales__icontains=q)
                    | Q(caso__cct__cct__icontains=q)
                    | Q(caso__cct_nombre__icontains=q)
                    | (Q(pk=int(q)) if is_numeric else Q())
                    | (Q(caso_id=int(q)) if is_numeric else Q())
                )
                .order_by("-fecha")[:25]
            )

        def serialize_caso(caso):
            return {
                "id": caso.pk,
                "label": f"Caso #{caso.pk} · {caso.cct_id} · {caso.cct_nombre or ''}",
                "asunto": caso.asunto or caso.descripcion_breve or "",
                "fecha": caso.fecha_apertura.strftime("%d/%m/%Y") if caso.fecha_apertura else "",
                "estatus": caso.estatus.nombre if caso.estatus else "Sin estatus",
                "cct": caso.cct_id or "",
                "cct_nombre": caso.cct_nombre or "",
                "asesor": caso.asesor_cct or "",
                "docente": caso.incidencia_nombre_docente or "",
                "jerarquia": "Caso base",
                "expediente": caso.numero_oficio or "",
            }

        def serialize_tramite(tramite):
            return {
                "id": tramite.pk,
                "label": f"Trámite #{tramite.pk} · Caso #{tramite.caso_id} · {tramite.tipo.nombre if tramite.tipo else ''}",
                "asunto": tramite.asunto or "",
                "fecha": tramite.fecha.strftime("%d/%m/%Y") if tramite.fecha else "",
                "estatus": tramite.estatus.nombre if tramite.estatus else "Sin estatus",
                "cct": tramite.caso.cct_id if tramite.caso_id else "",
                "docente": tramite.caso.incidencia_nombre_docente if tramite.caso_id else "",
                "jerarquia": "Trámite iniciador" if tramite.es_iniciador else "Trámite anexo",
                "tipo_tramite": tramite.tipo.nombre if tramite.tipo else "",
                "expediente": tramite.numero_oficio or "",
            }

        return JsonResponse(
            {
                "casos": [serialize_caso(c) for c in casos],
                "tramites": [serialize_tramite(t) for t in tramites],
            }
        )


class CasoInternoGenerarFolioView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.add_folioregistro"

    def post(self, request, *args, **kwargs):
        caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("pk"))
        if caso.numero_oficio:
            messages.warning(request, _("El caso ya tiene número de expediente."))
            return redirect(reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk}))
        registro = _generar_folio(usuario=request.user, tipo="caso", casos=[caso])
        caso.numero_oficio = registro.folio
        caso.save(update_fields=["numero_oficio", "actualizado_en"])
        messages.success(request, _("Folio generado correctamente."))
        return redirect(reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk}))


class TramiteCasoGenerarFolioView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.add_folioregistro"

    def post(self, request, *args, **kwargs):
        tramite = get_object_or_404(
            models.TramiteCaso, pk=kwargs.get("pk"), caso_id=kwargs.get("caso_pk")
        )
        if tramite.numero_oficio:
            messages.warning(request, _("El trámite ya tiene número de expediente."))
            return redirect(
                reverse(
                    "tramites:tramite-caso-detail",
                    kwargs={"caso_pk": tramite.caso_id, "pk": tramite.pk},
                )
            )
        registro = _generar_folio(usuario=request.user, tipo="tramite", tramite=tramite)
        tramite.numero_oficio = registro.folio
        tramite.save(update_fields=["numero_oficio", "actualizado_en"])
        messages.success(request, _("Folio generado correctamente."))
        return redirect(
            reverse(
                "tramites:tramite-caso-detail",
                kwargs={"caso_pk": tramite.caso_id, "pk": tramite.pk},
            )
        )


class DuplicadosPreviewView(LoginRequiredMixin, View):
    """Endpoint JSON para previsualizar duplicados antes de guardar."""

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        numero_oficio = (request.GET.get("numero_oficio") or "").strip()
        generador_nombre = (request.GET.get("generador_nombre") or "").strip()
        generador_iniciales = (request.GET.get("generador_iniciales") or "").strip()
        receptor_nombre = (request.GET.get("receptor_nombre") or "").strip()
        receptor_iniciales = (request.GET.get("receptor_iniciales") or "").strip()
        exclude_type = (request.GET.get("exclude_type") or "").strip()
        exclude_id = request.GET.get("exclude_id")
        exclude_caso_id = None
        exclude_tramite_id = None
        if exclude_id and exclude_id.isdigit():
            if exclude_type == "caso":
                exclude_caso_id = int(exclude_id)
            elif exclude_type == "tramite":
                exclude_tramite_id = int(exclude_id)
        casos_dup, tramites_dup = _buscar_duplicados_expediente(
            numero_oficio,
            exclude_caso_id=exclude_caso_id,
            exclude_tramite_id=exclude_tramite_id,
        )
        casos_part, tramites_part = _buscar_coincidencias_participantes(
            generador_nombre=generador_nombre,
            generador_iniciales=generador_iniciales,
            receptor_nombre=receptor_nombre,
            receptor_iniciales=receptor_iniciales,
            exclude_caso_id=exclude_caso_id,
            exclude_tramite_id=exclude_tramite_id,
        )

        def serialize_caso(caso: models.CasoInterno):
            return {
                "id": caso.pk,
                "type": "caso",
                "numero_oficio": caso.numero_oficio or "",
                "cct": caso.cct_id,
                "descripcion": caso.descripcion_breve,
                "url": reverse("tramites:casointerno-detail", kwargs={"pk": caso.pk}),
            }

        def serialize_tramite(tramite: models.TramiteCaso):
            return {
                "id": tramite.pk,
                "type": "tramite",
                "numero_oficio": tramite.numero_oficio or "",
                "caso_id": tramite.caso_id,
                "tipo": str(tramite.tipo),
                "fecha": tramite.fecha.isoformat() if tramite.fecha else "",
                "url": reverse(
                    "tramites:tramite-caso-detail",
                    kwargs={"caso_pk": tramite.caso_id, "pk": tramite.pk},
                ),
            }

        return JsonResponse(
            {
                "expediente": {
                    "casos": [serialize_caso(c) for c in casos_dup],
                    "tramites": [serialize_tramite(t) for t in tramites_dup],
                },
                "participantes": {
                    "casos": [serialize_caso(c) for c in casos_part],
                    "tramites": [serialize_tramite(t) for t in tramites_part],
                },
            }
        )

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["caso"] = self.object.caso
        ctx["prefijos_oficio"] = list(models.PrefijoOficio.objects.filter(esta_activo=True).order_by("nombre"))
        return ctx


class TramiteCasoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Elimina un trámite asociado a un caso previa confirmación."""

    permission_required = "licencias.delete_tramitecaso"
    model = models.TramiteCaso
    template_name = "tramites/tramites/tramite_caso_confirm_delete.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("caso")
        caso_pk = self.kwargs.get("caso_pk")
        if caso_pk:
            qs = qs.filter(caso_id=caso_pk)
        return qs

    def get_success_url(self):
        return reverse_lazy("tramites:casointerno-detail", kwargs={"pk": self.object.caso_id})

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        obj = self.get_object()
        inbox.notificar_tramite_eliminado(obj, actor=request.user)
        messages.success(request, _("Trámite eliminado."))
        return super().delete(request, *args, **kwargs)


class TramiteCasoEstatusCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Agrega un cambio de estatus a un trámite y actualiza el estatus actual."""

    permission_required = "licencias.change_tramitecaso"
    form_class = forms.HistorialEstatusTramiteCasoForm

    def dispatch(self, request, *args, **kwargs):
        self.tramite = get_object_or_404(
            models.TramiteCaso.objects.select_related("caso", "estatus"), pk=kwargs.get("tramite_pk")
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        nuevo_estatus = form.cleaned_data["estatus_nuevo"]
        comentario = form.cleaned_data.get("comentario", "")
        fecha_estatus = form.cleaned_data.get("fecha_estatus")
        anterior = (
            self.tramite.historial_estatus.order_by("-fecha_cambio", "-id")
            .values_list("estatus_nuevo", flat=True)
            .first()
        )
        estatus_anterior_obj = None
        if anterior:
            try:
                estatus_anterior_obj = models.EstatusTramite.objects.get(pk=anterior)
            except models.EstatusTramite.DoesNotExist:
                estatus_anterior_obj = self.tramite.estatus
        else:
            estatus_anterior_obj = self.tramite.estatus
        registrar_cambio_estatus_tramite(
            tramite=self.tramite,
            usuario=self.request.user,
            estatus_anterior=estatus_anterior_obj,
            estatus_nuevo=nuevo_estatus,
            comentario=comentario,
            fecha_estatus=fecha_estatus,
        )
        self.tramite.estatus = nuevo_estatus
        self.tramite.save(update_fields=["estatus", "actualizado_en"])
        messages.success(self.request, _("Estatus del trámite actualizado."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "tramites:tramite-caso-detail",
            kwargs={"caso_pk": self.tramite.caso_id, "pk": self.tramite.pk},
        )

    def form_invalid(self, form):
        messages.error(self.request, _("No se pudo registrar el cambio de estatus."))
        return redirect(
            "tramites:tramite-caso-detail",
            caso_pk=self.tramite.caso_id,
            pk=self.tramite.pk,
        )


class TramiteCasoEstatusUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edita el último cambio de estatus de un trámite."""

    permission_required = "licencias.change_tramitecaso"
    model = models.HistorialEstatusTramiteCaso
    form_class = forms.HistorialEstatusTramiteCasoForm
    template_name = "tramites/tramites/tramite_caso_status_form.html"
    context_object_name = "estatus_tramite"

    def get_queryset(self):
        return super().get_queryset().select_related("tramite", "estatus_anterior", "estatus_nuevo")

    def dispatch(self, request, *args, **kwargs):
        self.tramite = get_object_or_404(models.TramiteCaso, pk=kwargs.get("tramite_pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        ultimo = obj.tramite.historial_estatus.order_by("-fecha_cambio", "-id").first()
        if ultimo and ultimo.pk != obj.pk:
            messages.error(
                self.request,
                _("Solo puedes editar el último cambio de estatus para mantener la consistencia."),
            )
            raise Http404
        return obj

    def form_valid(self, form):
        old_status_id = (
            models.HistorialEstatusTramiteCaso.objects.filter(pk=self.object.pk)
            .values_list("estatus_nuevo_id", flat=True)
            .first()
        )
        old_status = models.EstatusTramite.objects.filter(pk=old_status_id).first()
        response = super().form_valid(form)
        self.tramite.estatus = form.cleaned_data["estatus_nuevo"]
        self.tramite.save(update_fields=["estatus", "actualizado_en"])
        inbox.notificar_tramite_estatus(
            tramite=self.tramite,
            estatus_anterior=old_status,
            estatus_nuevo=self.tramite.estatus,
            comentario="Estatus editado.",
            actor=self.request.user,
        )
        messages.success(self.request, _("Cambio de estatus actualizado."))
        return response

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["tramite"] = self.tramite
        return ctx

    def get_success_url(self):
        return reverse_lazy(
            "tramites:tramite-caso-detail",
            kwargs={"caso_pk": self.tramite.caso_id, "pk": self.tramite.pk},
        )


class TramiteCasoEstatusDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Elimina el último cambio de estatus de un trámite y revierte el estatus si aplica."""

    permission_required = "licencias.change_tramitecaso"
    model = models.HistorialEstatusTramiteCaso
    template_name = "tramites/tramites/tramite_caso_status_confirm_delete.html"
    context_object_name = "estatus_tramite"

    def get_queryset(self):
        return super().get_queryset().select_related("tramite", "estatus_anterior", "estatus_nuevo")

    def dispatch(self, request, *args, **kwargs):
        self.tramite = get_object_or_404(models.TramiteCaso, pk=kwargs.get("tramite_pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        ultimo = obj.tramite.historial_estatus.order_by("-fecha_cambio", "-id").first()
        if ultimo and ultimo.pk != obj.pk:
            messages.error(
                self.request,
                _("Solo puedes eliminar el último cambio de estatus para mantener la consistencia."),
            )
            raise Http404
        return obj

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        obj = self.get_object()
        old_status = obj.estatus_nuevo
        response = super().delete(request, *args, **kwargs)
        self.tramite.estatus = obtener_estatus_actual_tramite(self.tramite)
        self.tramite.save(update_fields=["estatus", "actualizado_en"])
        inbox.notificar_tramite_estatus(
            tramite=self.tramite,
            estatus_anterior=old_status,
            estatus_nuevo=self.tramite.estatus,
            comentario="Estatus eliminado.",
            actor=request.user,
        )
        messages.success(request, _("Cambio de estatus eliminado y estatus del trámite actualizado."))
        return response

    def get_success_url(self):
        return reverse_lazy(
            "tramites:tramite-caso-detail",
            kwargs={"caso_pk": self.tramite.caso_id, "pk": self.tramite.pk},
        )


class MinutaCasoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.change_casointerno"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        minuta = get_object_or_404(
            models.MinutaCaso.objects.select_related("caso"),
            pk=kwargs.get("minuta_pk"),
            caso_id=kwargs.get("pk"),
        )
        referencia = "Minuta adjunta eliminada."
        inbox.notificar_minuta_eliminada_caso(
            minuta.caso,
            actor=request.user,
            referencia=referencia,
        )
        minuta.delete()
        messages.success(request, _("Minuta eliminada."))
        next_url = request.POST.get("next") or reverse_lazy("tramites:casointerno-detail", kwargs={"pk": minuta.caso_id})
        return redirect(next_url)


class CasoInternoMinutaClearView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.change_casointerno"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("pk"))
        if caso.minuta:
            caso.minuta.delete(save=False)
            caso.minuta = None
            caso.save(update_fields=["minuta"])
            inbox.notificar_minuta_eliminada_caso(
                caso,
                actor=request.user,
                referencia="Minuta principal eliminada.",
            )
        messages.success(request, _("Minuta eliminada."))
        next_url = request.POST.get("next") or reverse_lazy("tramites:casointerno-update", kwargs={"pk": caso.pk})
        return redirect(next_url)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["tramite"] = self.tramite
        return ctx


class CasoInternoDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, DeleteView
):
    """Elimina un trámite previa confirmación."""

    permission_required = "licencias.delete_casointerno"
    model = models.CasoInterno
    template_name = "tramites/tramites/tramites_confirm_delete.html"
    success_url = reverse_lazy("tramites:casointerno-list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        obj = self.get_object()
        inbox.notificar_caso_eliminado(obj, actor=request.user)
        messages.success(request, _("Trámite eliminado."))
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return self.request.GET.get("from_list") or str(self.success_url)


class CasoInternoEstatusCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Agrega un cambio de estatus al trámite principal y actualiza su estatus actual."""

    permission_required = "licencias.change_casointerno"
    form_class = forms.HistorialEstatusCasoForm

    def dispatch(self, request, *args, **kwargs):
        self.caso = get_object_or_404(models.CasoInterno.objects.select_related("estatus"), pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        nuevo_estatus = form.cleaned_data["estatus_nuevo"]
        comentario = form.cleaned_data.get("comentario", "")
        fecha_estatus = form.cleaned_data.get("fecha_estatus")
        anterior = (
            self.caso.historial_estatus.order_by("-fecha_cambio", "-id")
            .values_list("estatus_nuevo", flat=True)
            .first()
        )
        estatus_anterior_obj = None
        if anterior:
            try:
                estatus_anterior_obj = models.EstatusCaso.objects.get(pk=anterior)
            except models.EstatusCaso.DoesNotExist:
                estatus_anterior_obj = self.caso.estatus
        else:
            estatus_anterior_obj = self.caso.estatus
        registrar_cambio_estatus_caso(
            caso=self.caso,
            usuario=self.request.user,
            estatus_anterior=estatus_anterior_obj,
            estatus_nuevo=nuevo_estatus,
            comentario=comentario,
            fecha_estatus=fecha_estatus,
        )
        self.caso.estatus = nuevo_estatus
        self.caso.save(update_fields=["estatus", "actualizado_en"])
        messages.success(self.request, _("Estatus del trámite actualizado."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("No se pudo registrar el cambio de estatus."))
        return redirect("tramites:casointerno-detail", pk=self.caso.pk)

    def get_success_url(self):
        return reverse_lazy("tramites:casointerno-detail", kwargs={"pk": self.caso.pk})


class CasoInternoEstatusUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Permite editar el último cambio de estatus del trámite principal."""

    permission_required = "licencias.change_casointerno"
    model = models.HistorialEstatusCaso
    form_class = forms.HistorialEstatusCasoForm
    template_name = "tramites/tramites/caso_estatus_form.html"
    context_object_name = "estatus_caso"

    def get_queryset(self):
        return super().get_queryset().select_related("caso", "estatus_anterior", "estatus_nuevo")

    def dispatch(self, request, *args, **kwargs):
        self.caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("pk"))
        self.estatus_pk = kwargs.get("estatus_pk")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        qs = queryset or self.get_queryset()
        obj = get_object_or_404(qs, pk=self.estatus_pk)
        ultimo = obj.caso.historial_estatus.order_by("-fecha_cambio", "-id").first()
        if ultimo and ultimo.pk != obj.pk:
            messages.error(
                self.request,
                _("Solo puedes editar el último cambio de estatus para mantener la consistencia."),
            )
            raise Http404
        return obj

    def form_valid(self, form):
        old_status_id = (
            models.HistorialEstatusCaso.objects.filter(pk=self.object.pk)
            .values_list("estatus_nuevo_id", flat=True)
            .first()
        )
        old_status = models.EstatusCaso.objects.filter(pk=old_status_id).first()
        response = super().form_valid(form)
        self.caso.estatus = form.cleaned_data["estatus_nuevo"]
        self.caso.save(update_fields=["estatus", "actualizado_en"])
        inbox.notificar_caso_estatus(
            caso=self.caso,
            estatus_anterior=old_status,
            estatus_nuevo=self.caso.estatus,
            comentario="Estatus editado.",
            actor=self.request.user,
        )
        messages.success(self.request, _("Cambio de estatus actualizado."))
        return response

    def get_success_url(self):
        return reverse_lazy("tramites:casointerno-detail", kwargs={"pk": self.caso.pk})

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["caso"] = self.caso
        return ctx


class CasoInternoEstatusDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Elimina el último cambio de estatus del trámite principal y revierte el estatus si aplica."""

    permission_required = "licencias.change_casointerno"
    model = models.HistorialEstatusCaso
    template_name = "tramites/tramites/caso_estatus_confirm_delete.html"
    context_object_name = "estatus_caso"

    def get_queryset(self):
        return super().get_queryset().select_related("caso", "estatus_anterior", "estatus_nuevo")

    def dispatch(self, request, *args, **kwargs):
        self.caso = get_object_or_404(models.CasoInterno, pk=kwargs.get("pk"))
        self.estatus_pk = kwargs.get("estatus_pk")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        qs = queryset or self.get_queryset()
        obj = get_object_or_404(qs, pk=self.estatus_pk)
        ultimo = obj.caso.historial_estatus.order_by("-fecha_cambio", "-id").first()
        if ultimo and ultimo.pk != obj.pk:
            messages.error(
                self.request,
                _("Solo puedes eliminar el último cambio de estatus para mantener la consistencia."),
            )
            raise Http404
        return obj

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        obj = self.get_object()
        old_status = obj.estatus_nuevo
        response = super().delete(request, *args, **kwargs)
        self.caso.estatus = obtener_estatus_actual_caso(self.caso)
        self.caso.save(update_fields=["estatus", "actualizado_en"])
        inbox.notificar_caso_estatus(
            caso=self.caso,
            estatus_anterior=old_status,
            estatus_nuevo=self.caso.estatus,
            comentario="Estatus eliminado.",
            actor=request.user,
        )
        messages.success(request, _("Cambio de estatus eliminado y estatus del trámite actualizado."))
        return response

    def get_success_url(self):
        return reverse_lazy("tramites:casointerno-detail", kwargs={"pk": self.caso.pk})


class MinutaTramiteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.change_tramitecaso"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        minuta = get_object_or_404(
            models.MinutaTramite.objects.select_related("tramite", "tramite__caso"),
            pk=kwargs.get("minuta_pk"),
            tramite_id=kwargs.get("tramite_pk"),
        )
        referencia = "Minuta adjunta eliminada."
        inbox.notificar_minuta_eliminada_tramite(
            minuta.tramite,
            actor=request.user,
            referencia=referencia,
        )
        minuta.delete()
        messages.success(request, _("Minuta eliminada."))
        next_url = request.POST.get("next") or reverse_lazy(
            "tramites:tramite-caso-detail",
            kwargs={"caso_pk": minuta.tramite.caso_id, "pk": minuta.tramite_id},
        )
        return redirect(next_url)


class TramiteMinutaClearView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "licencias.change_tramitecaso"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        tramite = get_object_or_404(models.TramiteCaso, pk=kwargs.get("tramite_pk"))
        if tramite.minuta:
            tramite.minuta.delete(save=False)
            tramite.minuta = None
            tramite.save(update_fields=["minuta"])
            inbox.notificar_minuta_eliminada_tramite(
                tramite,
                actor=request.user,
                referencia="Minuta principal eliminada.",
            )
        messages.success(request, _("Minuta eliminada."))
        next_url = request.POST.get("next") or reverse_lazy(
            "tramites:tramite-caso-update",
            kwargs={"caso_pk": tramite.caso_id, "pk": tramite.pk},
        )
        return redirect(next_url)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["caso"] = self.caso
        return ctx


class CCTLookupView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Devuelve información del CCT desde el catálogo de secundarias."""

    permission_required = "licencias.add_casointerno"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        codigo = (request.GET.get("cct") or "").strip().upper()
        if len(codigo) < 5:
            return JsonResponse({"found": False, "error": "CCT demasiado corto."}, status=200)
        ensure_cct_catalog_loaded()
        try:
            cct_obj = models.PlantillaCentroTrabajo.objects.get(cct__iexact=codigo)
        except models.PlantillaCentroTrabajo.DoesNotExist:
            return JsonResponse({"found": False}, status=200)
        return JsonResponse(
            {
                "found": True,
                "cct": cct_obj.cct,
                "c_nombre": cct_obj.nombre,
                "sostenimiento_c_subcontrol": normalise_sistema(cct_obj.sostenimiento),
                "tiponivelsub_c_servicion3": cct_obj.subnivel or "",
                "asesor": cct_obj.asesor or "",
            }
        )


class CCTSecundariaViewSet(viewsets.ModelViewSet):
    queryset = models.PlantillaCentroTrabajo.objects.all().order_by("cct")
    serializer_class = serializers.PlantillaCentroTrabajoSerializer
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = "cct"
    lookup_value_regex = "[^/]+"
    search_fields = ("cct", "nombre", "asesor", "subnivel", "municipio", "turno")
    ordering_fields = ("cct", "nombre", "municipio", "turno")

    def get_queryset(self):
        ensure_cct_catalog_loaded()
        return super().get_queryset()

    def get_object(self):
        lookup_value = self.kwargs.get(self.lookup_field)
        if lookup_value is None:
            return super().get_object()
        queryset = self.filter_queryset(self.get_queryset())
        try:
            return queryset.get(cct__iexact=lookup_value)
        except models.PlantillaCentroTrabajo.DoesNotExist as exc:
            raise Http404 from exc

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_plantillacentrotrabajo"):
            raise PermissionDenied("No tienes permisos para crear CCT.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_plantillacentrotrabajo"):
            raise PermissionDenied("No tienes permisos para editar CCT.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_plantillacentrotrabajo"):
            raise PermissionDenied("No tienes permisos para eliminar CCT.")
        instance.delete()


class TipoProcesoViewSet(viewsets.ModelViewSet):
    """API para gestionar tipos de trámite."""

    queryset = models.TipoProceso.objects.order_by("nombre")
    serializer_class = serializers.TipoProcesoSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_tipoproceso"):
            raise PermissionDenied("No tienes permisos para crear tipos de trámite.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_tipoproceso"):
            raise PermissionDenied("No tienes permisos para editar tipos de trámite.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_tipoproceso"):
            raise PermissionDenied("No tienes permisos para eliminar tipos de trámite.")
        instance.delete()


class EstatusCasoViewSet(viewsets.ModelViewSet):
    """API para gestionar estatus de caso."""

    queryset = models.EstatusCaso.objects.order_by("orden", "nombre")
    serializer_class = serializers.EstatusCasoSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre",)
    ordering_fields = ("nombre", "orden", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_estatuscaso"):
            raise PermissionDenied("No tienes permisos para crear estatus de caso.")
        try:
            serializer.save()
        except IntegrityError:
            nombre = serializer.validated_data.get("nombre", "").strip()
            raise ValidationError(
                {"nombre": f"El estatus '{nombre}' ya existe. Usa otro nombre."}
            )

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_estatuscaso"):
            raise PermissionDenied("No tienes permisos para editar estatus de caso.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_estatuscaso"):
            raise PermissionDenied("No tienes permisos para eliminar estatus de caso.")
        try:
            instance.delete()
        except dj_models.ProtectedError as exc:
            raise PermissionDenied(
                "No se puede eliminar el estatus porque está en uso en trámites o en su historial."
            ) from exc


class TipoViolenciaViewSet(viewsets.ModelViewSet):
    """API para gestionar tipos de violencia (opcional en el trámite)."""

    queryset = models.TipoViolencia.objects.order_by("nombre")
    serializer_class = serializers.TipoViolenciaSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_tipoviolencia"):
            raise PermissionDenied("No tienes permisos para crear tipos de violencia.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_tipoviolencia"):
            raise PermissionDenied("No tienes permisos para editar tipos de violencia.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_tipoviolencia"):
            raise PermissionDenied("No tienes permisos para eliminar tipos de violencia.")
        instance.delete()


class PrefijoOficioViewSet(viewsets.ModelViewSet):
    """API para gestionar prefijos sugeridos del número de oficio."""

    queryset = models.PrefijoOficio.objects.order_by("nombre")
    serializer_class = serializers.PrefijoOficioSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_prefijooficio"):
            raise PermissionDenied("No tienes permisos para crear prefijos de oficio.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_prefijooficio"):
            raise PermissionDenied("No tienes permisos para editar prefijos de oficio.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_prefijooficio"):
            raise PermissionDenied("No tienes permisos para eliminar prefijos de oficio.")


class FolioPrefijoViewSet(viewsets.ModelViewSet):
    """API para prefijos de folios."""

    queryset = models.FolioPrefijo.objects.order_by("nombre")
    serializer_class = serializers.FolioPrefijoSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_folioprefijo"):
            raise PermissionDenied("No tienes permisos para crear prefijos de folio.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_folioprefijo"):
            raise PermissionDenied("No tienes permisos para editar prefijos de folio.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_folioprefijo"):
            raise PermissionDenied("No tienes permisos para eliminar prefijos de folio.")
        instance.delete()


class SolicitanteViewSet(viewsets.ModelViewSet):
    """API para gestionar solicitantes."""

    queryset = models.Solicitante.objects.order_by("nombre")
    serializer_class = serializers.SolicitanteSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_solicitante"):
            raise PermissionDenied("No tienes permisos para crear solicitantes.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_solicitante"):
            raise PermissionDenied("No tienes permisos para editar solicitantes.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_solicitante"):
            raise PermissionDenied("No tienes permisos para eliminar solicitantes.")
        instance.delete()


class DestinatarioViewSet(viewsets.ModelViewSet):
    """API para gestionar destinatarios (dirigido a)."""

    queryset = models.Destinatario.objects.order_by("nombre")
    serializer_class = serializers.DestinatarioSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_destinatario"):
            raise PermissionDenied("No tienes permisos para crear destinatarios.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_destinatario"):
            raise PermissionDenied("No tienes permisos para editar destinatarios.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_destinatario"):
            raise PermissionDenied("No tienes permisos para eliminar destinatarios.")
        instance.delete()


class TramiteCasoViewSet(viewsets.ModelViewSet):
    """API para gestionar trámites adicionales de un caso."""

    queryset = models.TramiteCaso.objects.select_related("caso", "tipo", "estatus").order_by("-fecha", "-creado_en")
    serializer_class = serializers.TramiteCasoSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("asunto", "numero_oficio", "observaciones")
    ordering_fields = ("fecha", "creado_en")

    def get_queryset(self):
        qs = super().get_queryset()
        caso_id = self.request.query_params.get("caso")
        if caso_id:
            qs = qs.filter(caso_id=caso_id)
        return qs

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_tramitecaso"):
            raise PermissionDenied("No tienes permisos para crear trámites del caso.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_tramitecaso"):
            raise PermissionDenied("No tienes permisos para editar trámites del caso.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_tramitecaso"):
            raise PermissionDenied("No tienes permisos para eliminar trámites del caso.")
        instance.delete()


class EstatusTramiteViewSet(viewsets.ModelViewSet):
    """API para gestionar estatus de trámites asociados a casos."""

    queryset = models.EstatusTramite.objects.order_by("orden", "nombre")
    serializer_class = serializers.EstatusTramiteSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("nombre",)
    ordering_fields = ("nombre", "orden", "creado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_estatustramite"):
            raise PermissionDenied("No tienes permisos para crear estatus de trámite.")
        try:
            serializer.save()
        except IntegrityError:
            nombre = serializer.validated_data.get("nombre", "").strip()
            raise ValidationError(
                {"nombre": f"El estatus '{nombre}' ya existe. Usa otro nombre."}
            )

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_estatustramite"):
            raise PermissionDenied("No tienes permisos para editar estatus de trámite.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_estatustramite"):
            raise PermissionDenied("No tienes permisos para eliminar estatus de trámite.")
        instance.delete()


class SLAReglaViewSet(viewsets.ModelViewSet):
    """API para gestionar reglas SLA por tipo/estatus."""

    queryset = models.SLARegla.objects.select_related(
        "tipo_proceso",
        "estatus_caso",
        "estatus_tramite",
        "grupo_escalamiento",
    ).order_by("ambito", "tipo_proceso__nombre", "orden", "id")
    serializer_class = serializers.SLAReglaSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = (
        "nombre",
        "tipo_proceso__nombre",
        "estatus_caso__nombre",
        "estatus_tramite__nombre",
    )
    ordering_fields = ("ambito", "tipo_proceso__nombre", "dias_objetivo", "orden", "actualizado_en")

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                permissions.DjangoModelPermissions(),
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        if not self.request.user.has_perm("licencias.add_slaregla"):
            raise PermissionDenied("No tienes permisos para crear reglas SLA.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("licencias.change_slaregla"):
            raise PermissionDenied("No tienes permisos para editar reglas SLA.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("licencias.delete_slaregla"):
            raise PermissionDenied("No tienes permisos para eliminar reglas SLA.")
        instance.delete()


FOLIO_PREFIJO_DEFAULT = "SE/SEB/DES-EESP"
