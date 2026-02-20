from __future__ import annotations

import copy
import json
import unicodedata
from typing import Any

from tramites import models

AMBITO_CASO = models.PlantillaCapturaTipo.AMBITO_CASO
AMBITO_TRAMITE = models.PlantillaCapturaTipo.AMBITO_TRAMITE
NON_BLOCKING_REQUIRED_FIELDS = {"asunto"}

ALLOWED_FIELDS_BY_AMBITO: dict[str, set[str]] = {
    AMBITO_CASO: {
        "asunto",
        "numero_oficio",
        "solicitante",
        "dirigido_a",
        "tipo_prorroga",
        "sindicato",
        "diagnostico",
        "tipo_violencia",
        "fecha_termino",
        "incidencia_afiliacion",
        "incidencia_fecha_inicio",
        "incidencia_fecha_termino",
        "incidencia_dias_otorgados",
        "generador_nombre",
        "generador_iniciales",
        "generador_sexo",
        "receptor_nombre",
        "receptor_iniciales",
        "receptor_sexo",
        "observaciones_iniciales",
        "minuta",
        "minutas",
    },
    AMBITO_TRAMITE: {
        "asunto",
        "numero_oficio",
        "solicitante",
        "dirigido_a",
        "tipo_prorroga",
        "sindicato",
        "diagnostico",
        "tipo_violencia",
        "fecha_termino",
        "incidencia_afiliacion",
        "incidencia_fecha_inicio",
        "incidencia_fecha_termino",
        "incidencia_dias_otorgados",
        "generador_nombre",
        "generador_iniciales",
        "generador_sexo",
        "receptor_nombre",
        "receptor_iniciales",
        "receptor_sexo",
        "observaciones",
        "minuta",
        "minutas",
    },
}


def _normalize_text(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFKD", raw)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _dedupe_strings(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in values:
        cleaned = str(item or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


def _clean_field_list(values: Any, *, ambito: str) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    allowed = ALLOWED_FIELDS_BY_AMBITO.get(ambito, set())
    result: list[str] = []
    for value in values:
        field_name = str(value or "").strip()
        if field_name and field_name in allowed:
            result.append(field_name)
    return _dedupe_strings(result)


def _clean_required_field_list(values: Any, *, ambito: str) -> list[str]:
    cleaned = _clean_field_list(values, ambito=ambito)
    return [field_name for field_name in cleaned if field_name not in NON_BLOCKING_REQUIRED_FIELDS]


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "si", "sí", "yes"}:
            return True
        if lowered in {"0", "false", "no"}:
            return False
    return bool(value)


def _default_checklist_general() -> list[dict[str, Any]]:
    return [
        {
            "id": "apertura",
            "nombre": "Apertura",
            "descripcion": "Documentos base para dar de alta el trámite.",
            "bloquear_si_falta_critico": True,
            "documentos": [
                {"key": "solicitud_firmada", "nombre": "Solicitud firmada", "critico": True},
                {"key": "identificacion_trabajador", "nombre": "Identificación del trabajador", "critico": True},
                {"key": "oficio_turno", "nombre": "Oficio de turno", "critico": False},
            ],
        },
        {
            "id": "seguimiento",
            "nombre": "Seguimiento",
            "descripcion": "Soportes de la etapa de integración/seguimiento.",
            "bloquear_si_falta_critico": True,
            "documentos": [
                {"key": "evidencia_actuaciones", "nombre": "Evidencia de actuaciones", "critico": True},
                {"key": "acuses", "nombre": "Acuses de recibido", "critico": False},
            ],
        },
        {
            "id": "cierre",
            "nombre": "Cierre",
            "descripcion": "Documentos para concluir el trámite.",
            "bloquear_si_falta_critico": True,
            "documentos": [
                {"key": "resolucion_final", "nombre": "Resolución final", "critico": True},
                {"key": "minuta_cierre", "nombre": "Minuta de cierre", "critico": False},
            ],
        },
    ]


def _default_checklist_licencia() -> list[dict[str, Any]]:
    return [
        {
            "id": "apertura",
            "nombre": "Apertura",
            "descripcion": "Documentación inicial para licencias y cambios de función.",
            "bloquear_si_falta_critico": True,
            "documentos": [
                {"key": "solicitud_licencia", "nombre": "Solicitud de licencia", "critico": True},
                {"key": "dictamen_medico", "nombre": "Dictamen médico", "critico": True},
                {"key": "identificacion_oficial", "nombre": "Identificación oficial", "critico": False},
            ],
        },
        {
            "id": "seguimiento",
            "nombre": "Seguimiento",
            "descripcion": "Control de incidencias y validaciones.",
            "bloquear_si_falta_critico": True,
            "documentos": [
                {"key": "constancia_afiliacion", "nombre": "Constancia de afiliación", "critico": True},
                {"key": "acuse_recepcion", "nombre": "Acuse de recepción", "critico": False},
            ],
        },
        {
            "id": "cierre",
            "nombre": "Cierre",
            "descripcion": "Autorización y respaldo final.",
            "bloquear_si_falta_critico": True,
            "documentos": [
                {"key": "oficio_autorizacion", "nombre": "Oficio de autorización", "critico": True},
                {"key": "comprobante_notificacion", "nombre": "Comprobante de notificación", "critico": False},
            ],
        },
    ]


def _default_template(ambito: str, tipo_nombre: str = "") -> dict[str, Any]:
    if ambito not in {AMBITO_CASO, AMBITO_TRAMITE}:
        ambito = AMBITO_CASO

    observaciones_field = "observaciones_iniciales" if ambito == AMBITO_CASO else "observaciones"
    base_visible = [
        "asunto",
        "numero_oficio",
        "solicitante",
        "dirigido_a",
        observaciones_field,
        "fecha_termino",
        "minuta",
        "minutas",
    ]
    managed_fields = sorted(ALLOWED_FIELDS_BY_AMBITO[ambito])
    template = {
        "managed_fields": managed_fields,
        "default_visible_fields": _dedupe_strings(base_visible),
        "default_required_fields": [],
        "status_rules": [
            {
                "id": "prevencion",
                "match_any": ["prevencion", "prevencion de tramite", "incompleto"],
                "required_fields": [observaciones_field],
                "visible_fields": _dedupe_strings(base_visible + [observaciones_field]),
                "checklist_stage": "seguimiento",
            },
            {
                "id": "cierre",
                "match_any": ["concluido", "cerrado", "finalizado"],
                "required_fields": [],
                "visible_fields": _dedupe_strings(base_visible + ["fecha_termino", "minuta", "minutas"]),
                "checklist_stage": "cierre",
            },
        ],
        "checklist_etapas": _default_checklist_general(),
    }

    tipo_norm = _normalize_text(tipo_nombre)
    if "licenc" in tipo_norm or "prorrog" in tipo_norm:
        template["default_visible_fields"] = _dedupe_strings(
            base_visible
            + [
                "tipo_prorroga",
                "sindicato",
                "diagnostico",
                "incidencia_afiliacion",
                "incidencia_fecha_inicio",
                "incidencia_fecha_termino",
                "incidencia_dias_otorgados",
            ]
        )
        template["default_required_fields"] = ["tipo_prorroga"]
        template["checklist_etapas"] = _default_checklist_licencia()
    elif "violenc" in tipo_norm:
        template["default_visible_fields"] = _dedupe_strings(
            base_visible
            + [
                "tipo_violencia",
                "generador_nombre",
                "generador_iniciales",
                "generador_sexo",
                "receptor_nombre",
                "receptor_iniciales",
                "receptor_sexo",
            ]
        )
        template["default_required_fields"] = ["tipo_violencia"]
    return template


def _normalize_status_rules(raw_rules: Any, *, ambito: str) -> list[dict[str, Any]]:
    source: list[Any]
    if isinstance(raw_rules, dict):
        source = list(raw_rules.values())
    elif isinstance(raw_rules, (list, tuple)):
        source = list(raw_rules)
    else:
        source = []
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(source, start=1):
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "id": str(item.get("id") or f"regla-{idx}").strip(),
                "match_any": _dedupe_strings([_normalize_text(v) for v in item.get("match_any", [])]),
                "match_estatus_ids": _dedupe_strings([str(v).strip() for v in item.get("match_estatus_ids", [])]),
                "visible_fields": _clean_field_list(item.get("visible_fields"), ambito=ambito),
                "required_fields": _clean_required_field_list(item.get("required_fields"), ambito=ambito),
                "checklist_stage": str(item.get("checklist_stage") or "").strip(),
            }
        )
    return normalized


def _normalize_checklist(raw_stages: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_stages, (list, tuple)):
        return []
    stages: list[dict[str, Any]] = []
    seen_stage_ids: set[str] = set()
    for index, stage in enumerate(raw_stages, start=1):
        if not isinstance(stage, dict):
            continue
        stage_id = str(stage.get("id") or f"etapa-{index}").strip()
        if not stage_id or stage_id in seen_stage_ids:
            continue
        seen_stage_ids.add(stage_id)
        docs: list[dict[str, Any]] = []
        seen_doc_keys: set[str] = set()
        for doc_index, doc in enumerate(stage.get("documentos", []), start=1):
            if not isinstance(doc, dict):
                continue
            doc_key = str(doc.get("key") or f"doc-{doc_index}").strip()
            if not doc_key or doc_key in seen_doc_keys:
                continue
            seen_doc_keys.add(doc_key)
            docs.append(
                {
                    "key": doc_key,
                    "nombre": str(doc.get("nombre") or doc_key).strip(),
                    "critico": _as_bool(doc.get("critico"), default=False),
                    "descripcion": str(doc.get("descripcion") or "").strip(),
                }
            )
        if not docs:
            continue
        stages.append(
            {
                "id": stage_id,
                "nombre": str(stage.get("nombre") or stage_id).strip(),
                "descripcion": str(stage.get("descripcion") or "").strip(),
                "bloquear_si_falta_critico": _as_bool(stage.get("bloquear_si_falta_critico"), default=True),
                "documentos": docs,
            }
        )
    return stages


def normalize_template_payload(raw_template: dict[str, Any] | None, *, ambito: str, tipo_nombre: str) -> dict[str, Any]:
    merged = copy.deepcopy(_default_template(ambito, tipo_nombre=tipo_nombre))
    if not isinstance(raw_template, dict):
        return merged
    managed_fields = _clean_field_list(raw_template.get("managed_fields"), ambito=ambito)
    if managed_fields:
        merged["managed_fields"] = managed_fields
    default_visible = _clean_field_list(raw_template.get("default_visible_fields"), ambito=ambito)
    if default_visible:
        merged["default_visible_fields"] = default_visible
    default_required = _clean_required_field_list(raw_template.get("default_required_fields"), ambito=ambito)
    if default_required:
        merged["default_required_fields"] = default_required
    status_rules = _normalize_status_rules(raw_template.get("status_rules"), ambito=ambito)
    if status_rules:
        merged["status_rules"] = status_rules
    checklist_etapas = _normalize_checklist(raw_template.get("checklist_etapas"))
    if checklist_etapas:
        merged["checklist_etapas"] = checklist_etapas
    return merged


def _active_templates_map(ambito: str) -> dict[int, models.PlantillaCapturaTipo]:
    return {
        template.tipo_proceso_id: template
        for template in models.PlantillaCapturaTipo.objects.filter(
            ambito=ambito,
            esta_activa=True,
        ).select_related("tipo_proceso")
    }


def resolve_template_for_tipo(*, ambito: str, tipo_id: int | None, tipo_nombre: str = "") -> dict[str, Any]:
    tipo_name = str(tipo_nombre or "")
    if tipo_id:
        template = (
            models.PlantillaCapturaTipo.objects.filter(
                ambito=ambito,
                tipo_proceso_id=tipo_id,
                esta_activa=True,
            )
            .select_related("tipo_proceso")
            .first()
        )
        if template:
            payload = normalize_template_payload(
                {
                    "managed_fields": template.reglas_campos.get("managed_fields"),
                    "default_visible_fields": template.reglas_campos.get("default_visible_fields"),
                    "default_required_fields": template.reglas_campos.get("default_required_fields"),
                    "status_rules": template.reglas_campos.get("status_rules"),
                    "checklist_etapas": template.checklist_etapas,
                },
                ambito=ambito,
                tipo_nombre=template.tipo_proceso.nombre,
            )
            payload["template_id"] = template.pk
            payload["template_name"] = template.nombre or template.tipo_proceso.nombre
            return payload
    return normalize_template_payload({}, ambito=ambito, tipo_nombre=tipo_name)


def build_frontend_config(
    *,
    ambito: str,
    tipo_queryset,
    estatus_queryset,
    selected_tipo_id: int | None = None,
    selected_estatus_id: int | None = None,
    checklist_documental: dict[str, Any] | None = None,
) -> dict[str, Any]:
    templates_by_tipo: dict[str, dict[str, Any]] = {}
    active_templates = _active_templates_map(ambito)
    for tipo in tipo_queryset:
        template = active_templates.get(tipo.pk)
        if template:
            payload = normalize_template_payload(
                {
                    "managed_fields": template.reglas_campos.get("managed_fields"),
                    "default_visible_fields": template.reglas_campos.get("default_visible_fields"),
                    "default_required_fields": template.reglas_campos.get("default_required_fields"),
                    "status_rules": template.reglas_campos.get("status_rules"),
                    "checklist_etapas": template.checklist_etapas,
                },
                ambito=ambito,
                tipo_nombre=tipo.nombre,
            )
            payload["template_id"] = template.pk
            payload["template_name"] = template.nombre or tipo.nombre
        else:
            payload = normalize_template_payload({}, ambito=ambito, tipo_nombre=tipo.nombre)
            payload["template_id"] = None
            payload["template_name"] = tipo.nombre
        templates_by_tipo[str(tipo.pk)] = payload
    default_payload = normalize_template_payload({}, ambito=ambito, tipo_nombre="")
    return {
        "ambito": ambito,
        "templates_by_tipo": templates_by_tipo,
        "default_template": default_payload,
        "selected_tipo_id": str(selected_tipo_id) if selected_tipo_id else "",
        "selected_estatus_id": str(selected_estatus_id) if selected_estatus_id else "",
        "estatus": [{"id": str(status.pk), "nombre": status.nombre} for status in estatus_queryset],
        "checklist_documental": checklist_documental if isinstance(checklist_documental, dict) else {},
    }


def _match_status_rule(template: dict[str, Any], *, status_id: Any, status_nombre: str) -> dict[str, Any] | None:
    rules = template.get("status_rules") or []
    if not isinstance(rules, list):
        return None
    status_id_str = str(status_id or "").strip()
    status_norm = _normalize_text(status_nombre)
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        ids = {str(item).strip() for item in rule.get("match_estatus_ids", []) if str(item).strip()}
        if status_id_str and status_id_str in ids:
            return rule
        tokens = [_normalize_text(token) for token in rule.get("match_any", []) if token]
        if status_norm and any(token and token in status_norm for token in tokens):
            return rule
    return None


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _parse_checklist_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if payload in (None, ""):
        return {}
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return parsed
        except (TypeError, ValueError):
            return {}
    return {}


def _normalize_checklist_state(
    template: dict[str, Any],
    *,
    checklist_payload: dict[str, Any],
    status_rule: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    stages = template.get("checklist_etapas") or []
    if not isinstance(stages, list) or not stages:
        return {}, []
    stage_map = {
        str(stage.get("id")): stage
        for stage in stages
        if isinstance(stage, dict) and stage.get("id")
    }
    if not stage_map:
        return {}, []
    selected_stage = str(checklist_payload.get("stage") or "").strip()
    if not selected_stage and status_rule:
        selected_stage = str(status_rule.get("checklist_stage") or "").strip()
    if selected_stage not in stage_map:
        selected_stage = str(stages[0].get("id"))
    stage = stage_map.get(selected_stage) or stages[0]
    docs_def = stage.get("documentos") or []
    payload_items = checklist_payload.get("items")
    payload_map: dict[str, dict[str, Any]] = {}
    if isinstance(payload_items, list):
        for item in payload_items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            payload_map[key] = item
    normalized_items: list[dict[str, Any]] = []
    missing_critical: list[str] = []
    for doc in docs_def:
        key = str(doc.get("key") or "").strip()
        if not key:
            continue
        source = payload_map.get(key, {})
        checked = _as_bool(source.get("checked"), default=False)
        note = str(source.get("note") or "").strip()
        critical = _as_bool(doc.get("critico"), default=False)
        normalized_items.append(
            {
                "key": key,
                "nombre": str(doc.get("nombre") or key),
                "critico": critical,
                "checked": checked,
                "note": note,
            }
        )
        if critical and not checked:
            missing_critical.append(str(doc.get("nombre") or key))
    result = {
        "stage": selected_stage,
        "items": normalized_items,
    }
    return result, missing_critical


def validate_form_payload(
    form,
    cleaned_data: dict[str, Any],
    *,
    ambito: str,
    tipo_field: str,
    estatus_field: str,
    checklist_payload_field: str = "checklist_documental_payload",
    enforce_checklist_critical: bool = True,
) -> dict[str, Any]:
    tipo = cleaned_data.get(tipo_field)
    estatus = cleaned_data.get(estatus_field)
    tipo_id = getattr(tipo, "pk", None)
    tipo_nombre = getattr(tipo, "nombre", "")
    estatus_id = getattr(estatus, "pk", None)
    estatus_nombre = getattr(estatus, "nombre", "")
    template = resolve_template_for_tipo(
        ambito=ambito,
        tipo_id=tipo_id,
        tipo_nombre=tipo_nombre,
    )
    status_rule = _match_status_rule(template, status_id=estatus_id, status_nombre=estatus_nombre)
    required_fields = list(template.get("default_required_fields") or [])
    if status_rule:
        required_fields.extend(status_rule.get("required_fields") or [])
    for field_name in _dedupe_strings(required_fields):
        if field_name in NON_BLOCKING_REQUIRED_FIELDS:
            continue
        if field_name not in getattr(form, "fields", {}):
            continue
        if _is_empty(cleaned_data.get(field_name)):
            label = str(form.fields[field_name].label or field_name).strip()
            form.add_error(field_name, f"{label} es obligatorio para el tipo/estatus seleccionado.")

    payload = _parse_checklist_payload(cleaned_data.get(checklist_payload_field))
    has_payload = bool(payload)
    if not payload:
        payload = _parse_checklist_payload(cleaned_data.get("checklist_documental"))
        has_payload = bool(payload)
    if not has_payload:
        cleaned_data["checklist_documental"] = {}
        return cleaned_data
    checklist_state, missing_critical = _normalize_checklist_state(
        template,
        checklist_payload=payload,
        status_rule=status_rule,
    )
    if checklist_state:
        cleaned_data["checklist_documental"] = checklist_state
        stage_map = {
            str(stage.get("id")): stage
            for stage in template.get("checklist_etapas", [])
            if isinstance(stage, dict) and stage.get("id")
        }
        active_stage = stage_map.get(checklist_state.get("stage", ""))
        should_block = _as_bool(
            (active_stage or {}).get("bloquear_si_falta_critico"),
            default=True,
        )
        if enforce_checklist_critical and should_block and missing_critical:
            form.add_error(
                None,
                "Faltan documentos críticos en el checklist: "
                + ", ".join(missing_critical)
                + ".",
            )
    else:
        cleaned_data["checklist_documental"] = {}
    return cleaned_data
