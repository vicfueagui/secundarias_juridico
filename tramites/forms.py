"""Formularios para el registro y seguimiento de trámites."""
from __future__ import annotations

from datetime import date
import json
import re
import uuid

from django import forms
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        cleaned = []
        for item in data:
            cleaned.append(super().clean(item, initial))
        return cleaned

from tramites import models
from tramites.incidencias import normalise_incidencias
from tramites.services import captura_guiada
from tramites.utils import normalise_sistema


def _add_css_class(widget: forms.Widget, classname: str) -> None:
    clases = widget.attrs.get("class", "").split()
    if classname not in clases:
        clases.append(classname)
    widget.attrs["class"] = " ".join(filter(None, clases))


def _validate_pdf_file(archivo, *, field_label: str) -> None:
    if not archivo:
        return
    content_type = getattr(archivo, "content_type", "") or ""
    if content_type and content_type not in ("application/pdf", "application/x-pdf"):
        raise ValidationError(f"{field_label}: Solo se permiten archivos PDF.")
    try:
        header = archivo.read(4)
        archivo.seek(0)
    except Exception as exc:
        raise ValidationError(f"{field_label}: No se pudo validar el archivo.") from exc
    if header != b"%PDF":
        raise ValidationError(f"{field_label}: El archivo no parece ser un PDF válido.")


def _parse_json_value(raw_value, default):
    if raw_value in (None, "", [], {}):
        return default
    if isinstance(raw_value, (list, dict)):
        return raw_value
    try:
        data = json.loads(raw_value)
        return data
    except (TypeError, ValueError):
        return default


def _clear_optional_catalog_selection(
    form: forms.Form,
    cleaned: dict,
    *,
    field_name: str,
    search_keys: tuple[str, ...],
) -> None:
    if not getattr(form, "is_bound", False):
        return
    raw_value = None
    for key in search_keys:
        if key in form.data:
            raw_value = form.data.get(key)
            break
    if raw_value is None:
        return
    if str(raw_value or "").strip() == "":
        cleaned[field_name] = None


def _normalize_manual_workers(raw_value) -> list[dict[str, str]]:
    data = _parse_json_value(raw_value, [])
    if not isinstance(data, list):
        return []
    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre") or "").strip()
        if not nombre:
            continue
        worker_id = str(item.get("id") or "").strip()
        if not worker_id.startswith("manual:"):
            worker_id = f"manual:{uuid.uuid4().hex[:12]}"
        if worker_id in seen_ids:
            continue
        seen_ids.add(worker_id)
        normalized.append(
            {
                "id": worker_id,
                "nombre": nombre,
                "rfc": str(item.get("rfc") or "").strip().upper(),
                "curp": str(item.get("curp") or "").strip().upper(),
                "manual": True,
            }
        )
    return normalized


def _coerce_iso_date(raw_value) -> date | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, date):
        return raw_value
    try:
        return date.fromisoformat(str(raw_value).strip())
    except (TypeError, ValueError):
        return None


def _normalize_rangos_fechas(raw_value) -> list[dict[str, object]]:
    data = _parse_json_value(raw_value, [])
    if not isinstance(data, list):
        return []

    normalized: list[dict[str, object]] = []
    seen_ids: set[str] = set()

    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue

        trabajador_nombre = str(
            item.get("trabajador_nombre")
            or item.get("docente")
            or item.get("incidencia_nombre_docente")
            or ""
        ).strip()
        if not trabajador_nombre:
            raise forms.ValidationError(
                f"Rango adicional #{index}: selecciona el trabajador asociado."
            )

        payload = {
            "incidencia_nombre_docente": trabajador_nombre,
            "incidencia_afiliacion": str(item.get("incidencia_afiliacion") or "").strip().upper(),
            "incidencia_fecha_inicio": _coerce_iso_date(
                item.get("incidencia_fecha_inicio") or item.get("fecha_inicio")
            ),
            "incidencia_fecha_termino": _coerce_iso_date(
                item.get("incidencia_fecha_termino") or item.get("fecha_termino")
            ),
            "incidencia_dias_otorgados": item.get("incidencia_dias_otorgados"),
        }
        try:
            normalised = normalise_incidencias(payload, error_class=ValidationError)
        except ValidationError as exc:
            if getattr(exc, "message_dict", None):
                detail = "; ".join(
                    f"{field}: {', '.join(str(msg) for msg in messages)}"
                    for field, messages in exc.message_dict.items()
                )
            else:
                detail = "; ".join(str(msg) for msg in exc.messages)
            raise forms.ValidationError(f"Rango adicional #{index}: {detail}") from exc

        has_data = bool(
            normalised.get("incidencia_afiliacion")
            or normalised.get("incidencia_fecha_inicio")
            or normalised.get("incidencia_fecha_termino")
            or normalised.get("incidencia_dias_otorgados")
        )
        if not has_data:
            continue

        rango_id = str(item.get("id") or "").strip()
        if not rango_id:
            rango_id = f"rango:{uuid.uuid4().hex[:12]}"
        if rango_id in seen_ids:
            rango_id = f"rango:{uuid.uuid4().hex[:12]}"
        seen_ids.add(rango_id)

        normalized.append(
            {
                "id": rango_id,
                "trabajador_nombre": trabajador_nombre,
                "incidencia_afiliacion": normalised.get("incidencia_afiliacion") or "",
                "incidencia_fecha_inicio": (
                    normalised["incidencia_fecha_inicio"].isoformat()
                    if normalised.get("incidencia_fecha_inicio")
                    else ""
                ),
                "incidencia_fecha_termino": (
                    normalised["incidencia_fecha_termino"].isoformat()
                    if normalised.get("incidencia_fecha_termino")
                    else ""
                ),
                "incidencia_dias_otorgados": normalised.get("incidencia_dias_otorgados"),
            }
        )
    return normalized


def _worker_matches_lookup(worker: models.PlantillaEmpleado, raw_value: str) -> bool:
    token = (raw_value or "").strip().lower()
    if not token:
        return True
    candidates = {
        (worker.nombre or "").strip().lower(),
        (worker.rfc or "").strip().lower(),
        (worker.curp or "").strip().lower(),
    }
    candidates = {value for value in candidates if value}
    if token in candidates:
        return True
    if "·" in token:
        parts = [part.strip() for part in token.split("·") if part.strip()]
        if any(part in candidates for part in parts):
            return True
    if any(value and value in token for value in candidates):
        return True
    return False


def _find_single_worker_by_token(raw_value: str) -> models.PlantillaEmpleado | None:
    token = (raw_value or "").strip()
    if not token:
        return None
    lookup = lambda value: models.PlantillaEmpleado.objects.filter(
        Q(nombre__iexact=value) | Q(rfc__iexact=value) | Q(curp__iexact=value)
    )
    matches = lookup(token)
    if matches.count() == 1:
        return matches.first()
    if "·" in token:
        parts = [part.strip() for part in token.split("·") if part.strip()]
        for part in parts:
            matches = lookup(part)
            if matches.count() == 1:
                return matches.first()
    return None


def _manual_worker_matches_lookup(worker_data: dict[str, str], raw_value: str) -> bool:
    token = (raw_value or "").strip().lower()
    if not token:
        return True
    candidates = {
        str(worker_data.get("nombre") or "").strip().lower(),
        str(worker_data.get("rfc") or "").strip().lower(),
        str(worker_data.get("curp") or "").strip().lower(),
    }
    candidates = {value for value in candidates if value}
    if token in candidates:
        return True
    if "·" in token:
        parts = [part.strip() for part in token.split("·") if part.strip()]
        if any(part in candidates for part in parts):
            return True
    if any(value and value in token for value in candidates):
        return True
    return False


def _find_single_manual_worker_by_token(
    manual_workers: list[dict[str, str]], raw_value: str
) -> dict[str, str] | None:
    matches = [item for item in manual_workers if _manual_worker_matches_lookup(item, raw_value)]
    if len(matches) == 1:
        return matches[0]
    return None


def _extract_manual_workers_from_bound_form(form: forms.Form) -> list[dict[str, str]]:
    field_key = form.add_prefix("trabajadores_manuales")
    raw_value = form.data.get(field_key)
    if raw_value in (None, "") and field_key != "trabajadores_manuales":
        raw_value = form.data.get("trabajadores_manuales")
    return _normalize_manual_workers(raw_value)


def _upsert_manual_worker(item: dict[str, str]) -> models.PlantillaEmpleado | None:
    nombre = str(item.get("nombre") or "").strip()
    if not nombre:
        return None
    raw_rfc = str(item.get("rfc") or "").strip().upper()
    raw_curp = str(item.get("curp") or "").strip().upper()
    rfc = raw_rfc or None
    curp = raw_curp or None

    worker_id = str(item.get("id") or "").strip()
    existing = None
    if worker_id.isdigit():
        existing = models.PlantillaEmpleado.objects.filter(pk=int(worker_id)).first()
    if not existing and rfc:
        existing = models.PlantillaEmpleado.objects.filter(rfc__iexact=rfc).first()
    if not existing and curp:
        existing = models.PlantillaEmpleado.objects.filter(curp__iexact=curp).first()
    if not existing:
        same_name = models.PlantillaEmpleado.objects.filter(nombre__iexact=nombre)
        if same_name.count() == 1:
            existing = same_name.first()

    if existing:
        update_fields = []
        if nombre and existing.nombre != nombre:
            existing.nombre = nombre
            update_fields.append("nombre")
        if rfc and (existing.rfc or "").upper() != rfc:
            existing.rfc = rfc
            update_fields.append("rfc")
        if curp and (existing.curp or "").upper() != curp:
            existing.curp = curp
            update_fields.append("curp")
        if update_fields:
            update_fields.append("actualizado_en")
            existing.save(update_fields=update_fields)
        return existing

    try:
        return models.PlantillaEmpleado.objects.create(
            nombre=nombre,
            rfc=rfc,
            curp=curp,
        )
    except IntegrityError:
        fallback = None
        if rfc:
            fallback = models.PlantillaEmpleado.objects.filter(rfc__iexact=rfc).first()
        if not fallback and curp:
            fallback = models.PlantillaEmpleado.objects.filter(curp__iexact=curp).first()
        if fallback:
            return fallback
        raise


def _persist_manual_workers(
    manual_workers: list[dict[str, str]],
) -> dict[str, models.PlantillaEmpleado]:
    persisted: dict[str, models.PlantillaEmpleado] = {}
    for item in manual_workers:
        if not isinstance(item, dict):
            continue
        worker = _upsert_manual_worker(item)
        if not worker:
            continue
        persisted[str(item.get("id") or "")] = worker
    return persisted


class CCTReferenceFormMixin(forms.ModelForm):
    """Mixin para incorporar el patrón de captura y búsqueda de CCT."""

    cct_codigo = forms.CharField(
        label="CCT",
        max_length=12,
        help_text="Escribe la clave del centro de trabajo para autocompletar la información.",
    )
    cct_field_name = "cct"
    cct_nombre_field = "cct_nombre"
    cct_sistema_field = "cct_sistema"
    cct_modalidad_field = "cct_modalidad"
    cct_asesor_field = "asesor_cct"
    require_cct_codigo = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cct_field = self.fields.get(self.cct_field_name)
        if not cct_field:
            raise ValueError("El formulario debe definir un campo CCT para usar CCTReferenceFormMixin.")
        cct_field.queryset = models.PlantillaCentroTrabajo.objects.order_by("cct")
        cct_field.widget = forms.HiddenInput()
        cct_field.required = False

        cct_code_field = self.fields["cct_codigo"]
        cct_code_field.required = self.require_cct_codigo
        cct_code_field.widget.attrs.setdefault("list", "cct-options")
        cct_code_field.widget.attrs.setdefault("placeholder", "Ej. 31EES0001H")
        cct_code_field.widget.attrs.setdefault("autocomplete", "off")

        if self.instance and getattr(self.instance, "cct_id", None):
            cct_code_field.initial = self.instance.cct_id
        self._configure_cct_display_field(self.cct_nombre_field, "Se llenará con el nombre del CCT.")
        self._configure_cct_display_field(
            self.cct_sistema_field,
            "Sistema derivado del CCT.",
            label_override="Sistema",
        )
        self._configure_cct_display_field(
            self.cct_modalidad_field,
            "Modalidad derivada del CCT.",
            label_override="Modalidad",
        )
        self._configure_cct_display_field(
            self.cct_asesor_field,
            "Asesor responsable según el catálogo.",
            label_override="Asesor",
            readonly=False,
        )

    def _configure_cct_display_field(self, field_name, placeholder, *, label_override=None, readonly=True):
        if not field_name:
            return
        field = self.fields.get(field_name)
        if not field:
            return
        field.required = False
        if readonly:
            field.widget.attrs.setdefault("readonly", "readonly")
        field.widget.attrs.setdefault("placeholder", placeholder)
        if label_override:
            field.label = label_override

    def get_default_cct(self) -> models.PlantillaCentroTrabajo | None:
        return None

    def clean_cct_codigo(self) -> str:
        codigo = (self.cleaned_data.get("cct_codigo") or "").strip().upper()
        if not codigo:
            default_cct = self.get_default_cct()
            if default_cct:
                self.cleaned_data[self.cct_field_name] = default_cct
                self.instance.cct = default_cct
                self._apply_cct_data(default_cct)
                return ""
            if self.require_cct_codigo:
                raise forms.ValidationError("Debes proporcionar un CCT válido.")
            return ""
        try:
            cct_obj = models.PlantillaCentroTrabajo.objects.get(cct__iexact=codigo)
        except models.PlantillaCentroTrabajo.DoesNotExist as exc:
            raise forms.ValidationError("No se encontró el CCT en el catálogo.") from exc
        self.cleaned_data[self.cct_field_name] = cct_obj
        self.instance.cct = cct_obj
        self._apply_cct_data(cct_obj)
        return codigo

    def _apply_cct_data(self, cct_obj: models.PlantillaCentroTrabajo) -> None:
        if self.cct_nombre_field and self.cct_nombre_field in self.cleaned_data:
            self.cleaned_data[self.cct_nombre_field] = cct_obj.nombre
        if self.cct_sistema_field and self.cct_sistema_field in self.cleaned_data:
            self.cleaned_data[self.cct_sistema_field] = normalise_sistema(cct_obj.sostenimiento)
        if self.cct_modalidad_field and self.cct_modalidad_field in self.cleaned_data:
            self.cleaned_data[self.cct_modalidad_field] = cct_obj.subnivel or ""
        if (
            self.cct_asesor_field
            and self.cct_asesor_field in self.cleaned_data
            and not self.cleaned_data.get(self.cct_asesor_field)
        ):
            self.cleaned_data[self.cct_asesor_field] = cct_obj.asesor or ""

    def clean(self):
        cleaned = super().clean()
        cct_obj = cleaned.get(self.cct_field_name)
        if not cct_obj:
            cct_id = getattr(self.instance, "cct_id", None)
            if cct_id:
                cct_obj = models.PlantillaCentroTrabajo.objects.filter(pk=cct_id).first()
        if cct_obj:
            self.instance.cct = cct_obj
            if self.cct_nombre_field and self.cct_nombre_field in cleaned:
                cleaned[self.cct_nombre_field] = cleaned.get(self.cct_nombre_field) or cct_obj.nombre
            if self.cct_sistema_field and self.cct_sistema_field in cleaned:
                cleaned[self.cct_sistema_field] = normalise_sistema(
                    cleaned.get(self.cct_sistema_field) or cct_obj.sostenimiento
                )
            if self.cct_modalidad_field and self.cct_modalidad_field in cleaned:
                cleaned[self.cct_modalidad_field] = cleaned.get(self.cct_modalidad_field) or (cct_obj.subnivel or "")
            if self.cct_asesor_field and self.cct_asesor_field in cleaned and not cleaned.get(self.cct_asesor_field):
                cleaned[self.cct_asesor_field] = cct_obj.asesor or ""
        return cleaned


class CasoInternoForm(CCTReferenceFormMixin):
    """Formulario principal para registrar trámites."""

    trabajador_principal = forms.ModelChoiceField(
        queryset=models.PlantillaEmpleado.objects.none(),
        required=False,
        widget=forms.HiddenInput(),
    )
    trabajador_principal_nombre = forms.CharField(
        label="Nombre del trabajador",
        required=False,
        help_text="Busca por nombre, RFC o CURP para autocompletar la información.",
    )
    trabajadores_adicionales = forms.CharField(required=False, widget=forms.HiddenInput())
    trabajadores_centros = forms.CharField(required=False, widget=forms.HiddenInput())
    trabajadores_manuales = forms.CharField(required=False, widget=forms.HiddenInput())
    rangos_fechas_adicionales = forms.CharField(required=False, widget=forms.HiddenInput())
    centros_trabajo_adicionales = forms.CharField(required=False, widget=forms.HiddenInput())
    checklist_documental_payload = forms.CharField(required=False, widget=forms.HiddenInput())

    minutas = MultipleFileField(
        label="Minutas (PDF)",
        required=False,
        widget=MultipleFileInput(attrs={"multiple": True, "accept": "application/pdf"}),
        validators=[FileExtensionValidator(["pdf"])],
        help_text="Adjunta una o varias minutas en formato PDF.",
    )

    class Meta:
        model = models.CasoInterno
        fields = (
            "cct",
            "cct_nombre",
            "cct_sistema",
            "cct_modalidad",
            "asesor_cct",
            "usuarios_involucrados",
            "fecha_apertura",
            "fecha_termino",
            "estatus",
            "tipo_inicial",
            "tipo_violencia",
            "tipos_violencia_adicionales",
            "asunto",
            "minuta",
            "numero_oficio",
            "tipo_prorroga",
            "sindicato",
            "diagnostico",
            "solicitante",
            "dirigido_a",
            "generador_nombre",
            "generador_iniciales",
            "generador_sexo",
            "receptor_nombre",
            "receptor_iniciales",
            "receptor_sexo",
            "receptores_adicionales",
            "generadores_adicionales",
            "observaciones_iniciales",
            "incidencia_nombre_docente",
            "incidencia_afiliacion",
            "incidencia_fecha_inicio",
            "incidencia_fecha_termino",
            "incidencia_dias_otorgados",
            "rangos_fechas_adicionales",
            "checklist_documental",
        )
        widgets = {
            "fecha_apertura": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "fecha_termino": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "asunto": forms.Textarea(attrs={"rows": 3}),
            "observaciones_iniciales": forms.Textarea(attrs={"rows": 3}),
            "diagnostico": forms.Textarea(attrs={"rows": 3}),
            "receptores_adicionales": forms.HiddenInput(),
            "generadores_adicionales": forms.HiddenInput(),
            "tipos_violencia_adicionales": forms.HiddenInput(),
            "incidencia_fecha_inicio": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "incidencia_fecha_termino": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "incidencia_dias_otorgados": forms.NumberInput(attrs={"min": 1}),
            "rangos_fechas_adicionales": forms.HiddenInput(),
            "checklist_documental": forms.HiddenInput(),
            "minuta": forms.FileInput(attrs={"accept": "application/pdf"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuario_model = get_user_model()
        self.fields["usuarios_involucrados"].queryset = usuario_model.objects.order_by(
            "first_name",
            "last_name",
            "username",
        )
        self.fields["usuarios_involucrados"].widget = forms.CheckboxSelectMultiple(
            attrs={"class": "checkbox-list"}
        )
        self.fields["usuarios_involucrados"].help_text = (
            "Selecciona a los usuarios que deben recibir avisos en la bandeja."
        )
        self.fields["usuarios_involucrados"].required = False
        self.fields["usuarios_involucrados"].label_from_instance = (
            lambda user: f"{user.get_full_name() or user.username} ({user.email or 'sin correo'})"
        )
        if not self.is_bound and not self.instance.pk:
            default_usernames = [
                "maria.garciago",
                "admin",
                "dulce.luna",
                "claudio.diaz",
                "jaime.pacheco",
                "neggie.rubio",
            ]
            self.fields["usuarios_involucrados"].initial = [
                str(pk)
                for pk in usuario_model.objects.filter(username__in=default_usernames).values_list("pk", flat=True)
            ]
        self.fields["estatus"].queryset = models.EstatusCaso.objects.order_by("orden", "nombre")
        self.fields["tipo_inicial"].queryset = models.TipoProceso.objects.order_by("nombre")
        self.fields["fecha_apertura"].label = "Fecha del trámite"
        self.fields["fecha_termino"].required = False
        self.fields["fecha_termino"].label = "Fecha de término (opcional)"
        self.fields["numero_oficio"].widget.attrs.setdefault(
            "placeholder", "Ej. SE/SEB/DES-EESP/001/2024"
        )
        self.fields["numero_oficio"].widget.attrs.setdefault("list", "prefijo-oficio-options")
        self.fields["tipo_prorroga"].required = False
        self.fields["tipo_prorroga"].choices = [("", "---------")] + list(models.TIPO_PRORROGA_CHOICES)
        self.fields["sindicato"].required = False
        self.fields["sindicato"].choices = [("", "---------")] + list(models.SINDICATO_CHOICES)
        self.fields["diagnostico"].required = False
        for lic_field in ("tipo_prorroga", "sindicato", "diagnostico"):
            self.fields[lic_field].widget.attrs["data-captura-keep-visible"] = "true"
        self.fields["diagnostico"].widget.attrs.setdefault(
            "placeholder", "Describe el diagnóstico médico (opcional)."
        )
        self.fields["tipo_violencia"].required = False
        self.fields["tipo_violencia"].queryset = models.TipoViolencia.objects.order_by("nombre")
        # Mantener visible este campo aunque captura guiada oculte campos gestionados.
        self.fields["tipo_violencia"].widget.attrs["data-captura-keep-visible"] = "true"
        self.fields["solicitante"].required = False
        self.fields["solicitante"].queryset = models.Solicitante.objects.order_by("nombre")
        self.fields["dirigido_a"].required = False
        self.fields["dirigido_a"].queryset = models.Destinatario.objects.order_by("nombre")
        self.fields["minuta"].required = False
        self.fields["minuta"].label = "Documento (PDF)"
        self.fields["minuta"].help_text = "Adjunta el documento del trámite en formato PDF."
        self.fields["asunto"].widget.attrs.setdefault("placeholder", "Redacción libre del asunto del trámite.")
        self.fields["observaciones_iniciales"].required = False
        self.fields["observaciones_iniciales"].widget.attrs.setdefault(
            "placeholder", "Observaciones generales (opcional)."
        )
        sexo_choices = models.SEXO_NNA_CHOICES
        for field_name in ("generador_sexo", "receptor_sexo"):
            self.fields[field_name].required = False
            self.fields[field_name].choices = [("", "---------")] + list(sexo_choices)
        for optional_field in (
            "generador_nombre",
            "generador_iniciales",
            "receptor_nombre",
            "receptor_iniciales",
            "incidencia_nombre_docente",
            "incidencia_afiliacion",
            "incidencia_fecha_inicio",
            "incidencia_fecha_termino",
            "incidencia_dias_otorgados",
        ):
            self.fields[optional_field].required = False
        for rango_field in (
            "incidencia_afiliacion",
            "incidencia_fecha_inicio",
            "incidencia_fecha_termino",
            "incidencia_dias_otorgados",
        ):
            self.fields[rango_field].widget.attrs["data-captura-keep-visible"] = "true"
        self.fields["incidencia_dias_otorgados"].widget.attrs.setdefault("min", "1")
        self.fields["incidencia_dias_otorgados"].widget.attrs.setdefault("step", "1")
        self.fields["incidencia_nombre_docente"].widget = forms.HiddenInput()
        self.fields["trabajador_principal"].queryset = models.PlantillaEmpleado.objects.order_by("nombre")
        self.fields["trabajador_principal"].required = False
        self.fields["trabajador_principal_nombre"].widget.attrs.setdefault(
            "placeholder", "Escribe el nombre, RFC o CURP del trabajador"
        )
        self.fields["trabajador_principal_nombre"].widget.attrs.setdefault("data-trabajador-lookup", "true")
        self.fields["trabajador_principal_nombre"].widget.attrs.setdefault("list", "trabajador-options")
        self.fields["trabajador_principal"].widget.attrs.setdefault("data-trabajador-id", "true")
        self.fields["trabajadores_adicionales"].widget.attrs.setdefault("data-trabajadores-extra", "true")
        self.fields["trabajadores_centros"].widget.attrs.setdefault("data-trabajadores-centros-input", "true")
        self.fields["trabajadores_manuales"].widget.attrs.setdefault(
            "data-trabajadores-manuales", "true"
        )
        self.fields["centros_trabajo_adicionales"].widget.attrs.setdefault(
            "data-centros-adicionales-input", "true"
        )
        if self.instance and self.instance.pk:
            relacion_principal = (
                self.instance.trabajadores_caso.select_related("trabajador")
                .filter(es_principal=True)
                .first()
            )
            if relacion_principal:
                self.fields["trabajador_principal"].initial = relacion_principal.trabajador_id
                self.fields["trabajador_principal_nombre"].initial = (
                    relacion_principal.trabajador.nombre
                )
            adicionales = (
                self.instance.trabajadores_caso.select_related("trabajador")
                .filter(es_principal=False)
                .order_by("trabajador__nombre")
            )
            adicionales_data = [
                {
                    "id": rel.trabajador_id,
                    "nombre": rel.trabajador.nombre,
                    "rfc": rel.trabajador.rfc or "",
                    "curp": rel.trabajador.curp or "",
                }
                for rel in adicionales
            ]
            if adicionales_data:
                self.fields["trabajadores_adicionales"].initial = json.dumps(adicionales_data)
            centros_map = {}
            for rel in self.instance.trabajadores_caso.select_related("centro_trabajo_preferido"):
                if rel.centro_trabajo_preferido_id and rel.centro_trabajo_preferido:
                    centros_map[str(rel.trabajador_id)] = rel.centro_trabajo_preferido.cct
            if centros_map:
                self.fields["trabajadores_centros"].initial = json.dumps(centros_map)
            manuales_data = self.instance.trabajadores_manuales or []
            if manuales_data:
                self.fields["trabajadores_manuales"].initial = json.dumps(manuales_data)
            rangos_data = self.instance.rangos_fechas_adicionales or []
            if rangos_data:
                self.fields["rangos_fechas_adicionales"].initial = json.dumps(rangos_data)
            adicionales_centros = list(
                self.instance.centros_trabajo_adicionales.order_by("cct").values(
                    "cct", "nombre", "asesor", "sostenimiento", "subnivel"
                )
            )
            if adicionales_centros:
                for centro in adicionales_centros:
                    centro["sistema"] = normalise_sistema(centro.pop("sostenimiento", "") or "")
                    centro["modalidad"] = centro.pop("subnivel", "") or ""
                self.fields["centros_trabajo_adicionales"].initial = json.dumps(adicionales_centros)
            checklist_data = self.instance.checklist_documental or {}
            if checklist_data:
                serialized = json.dumps(checklist_data, ensure_ascii=False)
                self.fields["checklist_documental"].initial = serialized
                self.fields["checklist_documental_payload"].initial = serialized
        for name, field in self.fields.items():
            if name in {
                "cct",
                "cct_codigo",
                "usuarios_involucrados",
                "trabajador_principal",
                "trabajadores_adicionales",
                "trabajadores_centros",
                "trabajadores_manuales",
                "rangos_fechas_adicionales",
                "centros_trabajo_adicionales",
                "checklist_documental",
                "checklist_documental_payload",
            }:
                continue
            _add_css_class(field.widget, "form-input")
        _add_css_class(self.fields["cct_codigo"].widget, "form-input")
        _add_css_class(self.fields["trabajador_principal_nombre"].widget, "form-input")
        self.order_fields(
            [
                "trabajador_principal",
                "trabajador_principal_nombre",
                "trabajadores_adicionales",
                "trabajadores_centros",
                "trabajadores_manuales",
                "rangos_fechas_adicionales",
                "centros_trabajo_adicionales",
                "checklist_documental_payload",
                "checklist_documental",
                "cct",
                "cct_codigo",
                "cct_nombre",
                "cct_sistema",
                "cct_modalidad",
                "asesor_cct",
                "usuarios_involucrados",
                "tipo_inicial",
                "fecha_apertura",
                "fecha_termino",
                "tipo_violencia",
                "tipos_violencia_adicionales",
                "asunto",
                "minuta",
                "numero_oficio",
                "solicitante",
                "dirigido_a",
                "tipo_prorroga",
                "sindicato",
                "diagnostico",
                "generador_nombre",
                "generador_iniciales",
                "generador_sexo",
                "receptor_nombre",
                "receptor_iniciales",
                "receptor_sexo",
                "receptores_adicionales",
                "generadores_adicionales",
                "incidencia_nombre_docente",
                "incidencia_afiliacion",
                "incidencia_fecha_inicio",
                "incidencia_fecha_termino",
                "incidencia_dias_otorgados",
                "rangos_fechas_adicionales",
                "observaciones_iniciales",
                "estatus",
            ]
        )

    def clean_trabajador_principal_nombre(self) -> str:
        nombre = (self.cleaned_data.get("trabajador_principal_nombre") or "").strip()
        trabajador = self.cleaned_data.get("trabajador_principal")
        if not nombre and not trabajador:
            return ""
        if trabajador:
            if nombre and not _worker_matches_lookup(trabajador, nombre):
                self.cleaned_data["trabajador_principal"] = None
                trabajador = None
            else:
                return nombre or trabajador.nombre
        if not nombre:
            return ""
        matched_worker = _find_single_worker_by_token(nombre)
        if matched_worker:
            self.cleaned_data["trabajador_principal"] = matched_worker
            return nombre
        manual_workers = _extract_manual_workers_from_bound_form(self)
        manual_match = _find_single_manual_worker_by_token(manual_workers, nombre)
        if manual_match:
            self.cleaned_data["trabajador_principal_manual"] = manual_match
            return nombre
        raise forms.ValidationError("Selecciona un trabajador válido del catálogo.")

    def clean(self):
        cleaned = super().clean()
        _clear_optional_catalog_selection(
            self,
            cleaned,
            field_name="solicitante",
            search_keys=("caso_solicitante_busqueda", "solicitante_busqueda"),
        )
        _clear_optional_catalog_selection(
            self,
            cleaned,
            field_name="dirigido_a",
            search_keys=("caso_destinatario_busqueda", "destinatario_busqueda"),
        )
        adicionales_raw = cleaned.get("trabajadores_adicionales") or ""
        adicionales_data = _parse_json_value(adicionales_raw, [])
        adicionales_ids = []
        if isinstance(adicionales_data, list):
            for item in adicionales_data:
                if isinstance(item, dict):
                    raw_id = item.get("id") or item.get("pk")
                else:
                    raw_id = item
                if raw_id is None:
                    continue
                try:
                    adicionales_ids.append(int(raw_id))
                except (TypeError, ValueError):
                    continue
        cleaned["trabajadores_adicionales_ids"] = list(
            models.PlantillaEmpleado.objects.filter(id__in=adicionales_ids).values_list("id", flat=True)
        )
        centros_map_raw = cleaned.get("trabajadores_centros") or ""
        centros_map = _parse_json_value(centros_map_raw, {})
        if not isinstance(centros_map, dict):
            centros_map = {}
        cleaned["trabajadores_centros_map"] = {
            str(key): str(value)
            for key, value in centros_map.items()
            if value is not None and str(value).strip() != ""
        }
        principal = cleaned.get("trabajador_principal")
        if principal and principal.id in cleaned["trabajadores_adicionales_ids"]:
            cleaned["trabajadores_adicionales_ids"] = [
                pk for pk in cleaned["trabajadores_adicionales_ids"] if pk != principal.id
            ]
        has_primary_rango = bool(
            cleaned.get("incidencia_afiliacion")
            or cleaned.get("incidencia_fecha_inicio")
            or cleaned.get("incidencia_fecha_termino")
            or cleaned.get("incidencia_dias_otorgados") not in (None, "")
        )
        if not has_primary_rango:
            cleaned["incidencia_nombre_docente"] = ""
        elif not (cleaned.get("incidencia_nombre_docente") or "").strip():
            if principal:
                cleaned["incidencia_nombre_docente"] = principal.nombre
            else:
                cleaned["incidencia_nombre_docente"] = (
                    cleaned.get("trabajador_principal_nombre") or ""
                ).strip()
        cleaned["rangos_fechas_adicionales"] = _normalize_rangos_fechas(
            cleaned.get("rangos_fechas_adicionales") or []
        )
        cleaned["trabajadores_manuales_data"] = _normalize_manual_workers(
            cleaned.get("trabajadores_manuales") or ""
        )
        principal_manual = self.cleaned_data.get("trabajador_principal_manual")
        if not cleaned.get("trabajador_principal") and isinstance(principal_manual, dict):
            manual_match = next(
                (
                    item
                    for item in cleaned["trabajadores_manuales_data"]
                    if str(item.get("id") or "").strip()
                    == str(principal_manual.get("id") or "").strip()
                ),
                None,
            )
            if not manual_match:
                manual_match = _find_single_manual_worker_by_token(
                    cleaned["trabajadores_manuales_data"],
                    cleaned.get("trabajador_principal_nombre") or "",
                )
            if manual_match:
                cleaned["trabajador_principal_manual_data"] = manual_match
        adicionales_centros_raw = cleaned.get("centros_trabajo_adicionales") or ""
        adicionales_centros = _parse_json_value(adicionales_centros_raw, [])
        adicionales_ccts = []
        if isinstance(adicionales_centros, list):
            for item in adicionales_centros:
                if isinstance(item, dict):
                    cct = item.get("cct") or item.get("codigo")
                else:
                    cct = item
                if not cct:
                    continue
                cct = str(cct).strip().upper()
                if cct:
                    adicionales_ccts.append(cct)
        cct_principal = (cleaned.get("cct_codigo") or "").strip().upper()
        if not cct_principal and cleaned.get("cct"):
            cct_principal = cleaned["cct"].cct
        adicionales_ccts = [
            cct for cct in dict.fromkeys(adicionales_ccts) if cct and cct != cct_principal
        ]
        cleaned["centros_trabajo_adicionales_codes"] = adicionales_ccts
        cleaned = captura_guiada.validate_form_payload(
            self,
            cleaned,
            ambito=captura_guiada.AMBITO_CASO,
            tipo_field="tipo_inicial",
            estatus_field="estatus",
            enforce_checklist_critical=False,
        )
        return cleaned

    def save_trabajadores(self, caso: models.CasoInterno) -> None:
        principal = self.cleaned_data.get("trabajador_principal")
        adicionales_ids = self.cleaned_data.get("trabajadores_adicionales_ids", [])
        centros_map = self.cleaned_data.get("trabajadores_centros_map", {})
        manuales = self.cleaned_data.get("trabajadores_manuales_data", [])
        manuales_persistidos = _persist_manual_workers(manuales)

        ids = set(adicionales_ids)
        if principal:
            ids.add(principal.id)
        ids.update(worker.id for worker in manuales_persistidos.values())

        if not principal:
            principal_manual = self.cleaned_data.get("trabajador_principal_manual_data")
            if isinstance(principal_manual, dict):
                principal_worker = manuales_persistidos.get(
                    str(principal_manual.get("id") or "").strip()
                )
                if principal_worker:
                    principal = principal_worker
                    ids.add(principal.id)

        existing = {
            rel.trabajador_id: rel
            for rel in models.CasoTrabajador.objects.filter(caso=caso)
        }

        for trabajador_id, rel in list(existing.items()):
            if trabajador_id not in ids:
                rel.delete()

        for trabajador_id in ids:
            rel = existing.get(trabajador_id)
            if not rel:
                rel = models.CasoTrabajador(caso=caso, trabajador_id=trabajador_id)
            rel.es_principal = bool(principal and trabajador_id == principal.id)
            codigo = ""
            if str(trabajador_id) in centros_map:
                codigo = centros_map.get(str(trabajador_id), "").strip()
            centro = None
            if codigo:
                centro = models.PlantillaCentroTrabajo.objects.filter(cct__iexact=codigo).first()
            rel.centro_trabajo_preferido = centro
            rel.save()

        manuales_restantes: list[dict[str, str]] = []
        if caso.trabajadores_manuales != manuales_restantes:
            caso.trabajadores_manuales = manuales_restantes
            caso.save(update_fields=["trabajadores_manuales", "actualizado_en"])

    def save_centros_trabajo_adicionales(self, caso: models.CasoInterno) -> None:
        codes = self.cleaned_data.get("centros_trabajo_adicionales_codes", [])
        if not isinstance(codes, (list, tuple)):
            codes = []
        codes = [str(c).strip().upper() for c in codes if str(c).strip()]
        centros = list(models.PlantillaCentroTrabajo.objects.filter(cct__in=codes))
        caso.centros_trabajo_adicionales.set(centros)


class TramiteCasoForm(CCTReferenceFormMixin):
    require_cct_codigo = False
    trabajador_principal = forms.ModelChoiceField(
        queryset=models.PlantillaEmpleado.objects.none(),
        required=False,
        widget=forms.HiddenInput(),
    )
    trabajador_principal_nombre = forms.CharField(
        label="Nombre del trabajador",
        required=False,
        help_text="Busca por nombre, RFC o CURP para autocompletar la información.",
    )
    trabajadores_adicionales = forms.CharField(required=False, widget=forms.HiddenInput())
    trabajadores_centros = forms.CharField(required=False, widget=forms.HiddenInput())
    trabajadores_manuales = forms.CharField(required=False, widget=forms.HiddenInput())
    checklist_documental_payload = forms.CharField(required=False, widget=forms.HiddenInput())

    minutas = MultipleFileField(
        label="Minutas (PDF)",
        required=False,
        widget=MultipleFileInput(attrs={"multiple": True, "accept": "application/pdf"}),
        validators=[FileExtensionValidator(["pdf"])],
        help_text="Adjunta una o varias minutas en formato PDF.",
    )

    class Meta:
        model = models.TramiteCaso
        fields = (
            "cct",
            "cct_codigo",
            "cct_nombre",
            "cct_sistema",
            "cct_modalidad",
            "asesor_cct",
            "tipo",
            "usuarios_involucrados",
            "estatus",
            "fecha",
            "fecha_termino",
            "numero_oficio",
            "solicitante",
            "dirigido_a",
            "tipo_prorroga",
            "sindicato",
            "diagnostico",
            "tipo_violencia",
            "tipos_violencia_adicionales",
            "asunto",
            "minuta",
            "observaciones",
            "generador_nombre",
            "generador_iniciales",
            "generador_sexo",
            "receptor_nombre",
            "receptor_iniciales",
            "receptor_sexo",
            "receptores_adicionales",
            "generadores_adicionales",
            "incidencia_nombre_docente",
            "incidencia_afiliacion",
            "incidencia_fecha_inicio",
            "incidencia_fecha_termino",
            "incidencia_dias_otorgados",
            "rangos_fechas_adicionales",
            "checklist_documental",
        )
        widgets = {
            "fecha": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "fecha_termino": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
            "diagnostico": forms.Textarea(attrs={"rows": 3}),
            "receptores_adicionales": forms.HiddenInput(),
            "generadores_adicionales": forms.HiddenInput(),
            "tipos_violencia_adicionales": forms.HiddenInput(),
            "incidencia_fecha_inicio": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "incidencia_fecha_termino": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "incidencia_dias_otorgados": forms.NumberInput(attrs={"min": 1}),
            "rangos_fechas_adicionales": forms.HiddenInput(),
            "checklist_documental": forms.HiddenInput(),
            "minuta": forms.FileInput(attrs={"accept": "application/pdf"}),
        }

    def __init__(self, *args, **kwargs):
        self.caso = kwargs.pop("caso", None)
        super().__init__(*args, **kwargs)
        if self.caso is None and self.instance and getattr(self.instance, "caso_id", None):
            self.caso = self.instance.caso

        usuario_model = get_user_model()
        self.fields["usuarios_involucrados"].queryset = usuario_model.objects.order_by(
            "first_name",
            "last_name",
            "username",
        )
        self.fields["usuarios_involucrados"].widget = forms.CheckboxSelectMultiple(
            attrs={"class": "checkbox-list"}
        )
        self.fields["usuarios_involucrados"].help_text = (
            "Selecciona a los usuarios que deben recibir avisos en la bandeja."
        )
        self.fields["usuarios_involucrados"].required = False
        self.fields["usuarios_involucrados"].label_from_instance = (
            lambda user: f"{user.get_full_name() or user.username} ({user.email or 'sin correo'})"
        )
        self.fields["tipo"].queryset = models.TipoProceso.objects.order_by("nombre")
        self.fields["estatus"].queryset = models.EstatusTramite.objects.order_by("orden", "nombre")
        self.fields["estatus"].widget.attrs.setdefault("data-estatus-api", "/api/estatus-tramite/")
        self.fields["estatus"].widget.attrs.setdefault("data-estatus-label", "estatus de trámite")
        self.fields["tipo_violencia"].queryset = models.TipoViolencia.objects.order_by("nombre")
        self.fields["tipo_violencia"].required = False
        # Mantener visible este campo aunque captura guiada oculte campos gestionados.
        self.fields["tipo_violencia"].widget.attrs["data-captura-keep-visible"] = "true"
        self.fields["tipo_prorroga"].required = False
        self.fields["tipo_prorroga"].choices = [("", "---------")] + list(models.TIPO_PRORROGA_CHOICES)
        self.fields["sindicato"].required = False
        self.fields["sindicato"].choices = [("", "---------")] + list(models.SINDICATO_CHOICES)
        self.fields["diagnostico"].required = False
        for lic_field in ("tipo_prorroga", "sindicato", "diagnostico"):
            self.fields[lic_field].widget.attrs["data-captura-keep-visible"] = "true"
        self.fields["solicitante"].queryset = models.Solicitante.objects.order_by("nombre")
        self.fields["solicitante"].required = False
        self.fields["dirigido_a"].queryset = models.Destinatario.objects.order_by("nombre")
        self.fields["dirigido_a"].required = False
        self.fields["fecha_termino"].required = False
        self.fields["fecha_termino"].label = "Fecha de término (opcional)"
        self.fields["numero_oficio"].widget.attrs.setdefault("list", "prefijo-oficio-options")
        self.fields["diagnostico"].widget.attrs.setdefault(
            "placeholder", "Describe el diagnóstico médico (opcional)."
        )
        self.fields["minuta"].required = False
        self.fields["minuta"].label = "Documento (PDF)"
        self.fields["minuta"].help_text = "Adjunta el documento del trámite en formato PDF."

        sexo_choices = models.SEXO_NNA_CHOICES
        for field_name in ("generador_sexo", "receptor_sexo"):
            self.fields[field_name].required = False
            self.fields[field_name].choices = [("", "---------")] + list(sexo_choices)
        for optional_field in (
            "generador_nombre",
            "generador_iniciales",
            "receptor_nombre",
            "receptor_iniciales",
            "incidencia_nombre_docente",
            "incidencia_afiliacion",
            "incidencia_fecha_inicio",
            "incidencia_fecha_termino",
            "incidencia_dias_otorgados",
            "rangos_fechas_adicionales",
        ):
            self.fields[optional_field].required = False
        for rango_field in (
            "incidencia_afiliacion",
            "incidencia_fecha_inicio",
            "incidencia_fecha_termino",
            "incidencia_dias_otorgados",
        ):
            self.fields[rango_field].widget.attrs["data-captura-keep-visible"] = "true"
        self.fields["incidencia_dias_otorgados"].widget.attrs.setdefault("min", "1")
        self.fields["incidencia_dias_otorgados"].widget.attrs.setdefault("step", "1")
        self.fields["incidencia_nombre_docente"].widget = forms.HiddenInput()
        self.fields["numero_oficio"].widget.attrs.setdefault("placeholder", "Ej. SE/SEB/DES-EESP/001/2024")
        self.fields["asunto"].widget.attrs.setdefault("placeholder", "Descripción breve del trámite asociado.")

        self.fields["trabajador_principal"].queryset = models.PlantillaEmpleado.objects.order_by("nombre")
        self.fields["trabajador_principal"].required = False
        self.fields["trabajador_principal_nombre"].widget.attrs.setdefault(
            "placeholder", "Escribe el nombre, RFC o CURP del trabajador"
        )
        self.fields["trabajador_principal_nombre"].widget.attrs.setdefault("data-trabajador-lookup", "true")
        self.fields["trabajador_principal_nombre"].widget.attrs.setdefault("list", "trabajador-options")
        self.fields["trabajador_principal"].widget.attrs.setdefault("data-trabajador-id", "true")
        self.fields["trabajadores_adicionales"].widget.attrs.setdefault("data-trabajadores-extra", "true")
        self.fields["trabajadores_centros"].widget.attrs.setdefault("data-trabajadores-centros-input", "true")
        self.fields["trabajadores_manuales"].widget.attrs.setdefault(
            "data-trabajadores-manuales", "true"
        )

        if self.caso and self.caso.pk:
            if not self.is_bound and (not self.instance.pk or not self.instance.cct_id):
                self.fields["cct"].initial = self.caso.cct_id
                self.fields["cct_codigo"].initial = self.caso.cct_id
                self.fields["cct_nombre"].initial = self.caso.cct_nombre
                self.fields["cct_sistema"].initial = self.caso.cct_sistema
                self.fields["cct_modalidad"].initial = self.caso.cct_modalidad
                self.fields["asesor_cct"].initial = self.caso.asesor_cct
            self._set_trabajadores_initial_from_caso(self.caso)
            if not self.instance.pk and not self.is_bound:
                self._set_inherited_worker_initials(self.caso)
        if self.instance and self.instance.pk and not self.is_bound:
            rangos_data = self.instance.rangos_fechas_adicionales or []
            if rangos_data:
                self.fields["rangos_fechas_adicionales"].initial = rangos_data
            checklist_data = self.instance.checklist_documental or {}
            if checklist_data:
                serialized = json.dumps(checklist_data, ensure_ascii=False)
                self.fields["checklist_documental"].initial = serialized
                self.fields["checklist_documental_payload"].initial = serialized

        for name, field in self.fields.items():
            if name in {
                "usuarios_involucrados",
                "trabajador_principal",
                "trabajadores_adicionales",
                "trabajadores_centros",
                "trabajadores_manuales",
                "rangos_fechas_adicionales",
                "checklist_documental",
                "checklist_documental_payload",
                "cct",
            }:
                continue
            _add_css_class(field.widget, "form-input")
        _add_css_class(self.fields["trabajador_principal_nombre"].widget, "form-input")
        _add_css_class(self.fields["cct_codigo"].widget, "form-input")

    def get_default_cct(self) -> models.PlantillaCentroTrabajo | None:
        if self.caso and getattr(self.caso, "cct_id", None):
            return self.caso.cct
        return None

    def _set_trabajadores_initial_from_caso(self, caso: models.CasoInterno) -> None:
        relacion_principal = (
            caso.trabajadores_caso.select_related("trabajador")
            .filter(es_principal=True)
            .first()
        )
        if relacion_principal:
            self.fields["trabajador_principal"].initial = relacion_principal.trabajador_id
            self.fields["trabajador_principal_nombre"].initial = relacion_principal.trabajador.nombre
        adicionales = (
            caso.trabajadores_caso.select_related("trabajador")
            .filter(es_principal=False)
            .order_by("trabajador__nombre")
        )
        adicionales_data = [
            {
                "id": rel.trabajador_id,
                "nombre": rel.trabajador.nombre,
                "rfc": rel.trabajador.rfc or "",
                "curp": rel.trabajador.curp or "",
            }
            for rel in adicionales
        ]
        if adicionales_data:
            self.fields["trabajadores_adicionales"].initial = json.dumps(adicionales_data)
        centros_map = {}
        for rel in caso.trabajadores_caso.select_related("centro_trabajo_preferido"):
            if rel.centro_trabajo_preferido_id and rel.centro_trabajo_preferido:
                centros_map[str(rel.trabajador_id)] = rel.centro_trabajo_preferido.cct
        if centros_map:
            self.fields["trabajadores_centros"].initial = json.dumps(centros_map)
        manuales_data = caso.trabajadores_manuales or []
        if manuales_data:
            self.fields["trabajadores_manuales"].initial = json.dumps(manuales_data)

    def _set_inherited_worker_initials(self, caso: models.CasoInterno) -> None:
        self.fields["generador_nombre"].initial = caso.generador_nombre or ""
        self.fields["generador_iniciales"].initial = caso.generador_iniciales or ""
        self.fields["generador_sexo"].initial = caso.generador_sexo or ""
        self.fields["receptor_nombre"].initial = caso.receptor_nombre or ""
        self.fields["receptor_iniciales"].initial = caso.receptor_iniciales or ""
        self.fields["receptor_sexo"].initial = caso.receptor_sexo or ""
        self.fields["generadores_adicionales"].initial = caso.generadores_adicionales or []
        self.fields["receptores_adicionales"].initial = caso.receptores_adicionales or []
        self.fields["incidencia_nombre_docente"].initial = caso.incidencia_nombre_docente or ""
        self.fields["incidencia_afiliacion"].initial = caso.incidencia_afiliacion or ""
        self.fields["incidencia_fecha_inicio"].initial = caso.incidencia_fecha_inicio
        self.fields["incidencia_fecha_termino"].initial = caso.incidencia_fecha_termino
        self.fields["incidencia_dias_otorgados"].initial = caso.incidencia_dias_otorgados
        self.fields["rangos_fechas_adicionales"].initial = caso.rangos_fechas_adicionales or []

    def clean_minuta(self):
        archivo = self.cleaned_data.get("minuta")
        _validate_pdf_file(archivo, field_label="Documento (PDF)")
        return archivo

    def clean_minutas(self):
        archivos = self.cleaned_data.get("minutas") or []
        for archivo in archivos:
            _validate_pdf_file(archivo, field_label="Minutas (PDF)")
        return archivos

    def clean_trabajador_principal_nombre(self) -> str:
        nombre = (self.cleaned_data.get("trabajador_principal_nombre") or "").strip()
        trabajador = self.cleaned_data.get("trabajador_principal")
        if not nombre and not trabajador:
            return ""
        if trabajador:
            if nombre and not _worker_matches_lookup(trabajador, nombre):
                self.cleaned_data["trabajador_principal"] = None
                trabajador = None
            else:
                return nombre or trabajador.nombre
        if not nombre:
            return ""
        matched_worker = _find_single_worker_by_token(nombre)
        if matched_worker:
            self.cleaned_data["trabajador_principal"] = matched_worker
            return nombre
        manual_workers = _extract_manual_workers_from_bound_form(self)
        manual_match = _find_single_manual_worker_by_token(manual_workers, nombre)
        if manual_match:
            self.cleaned_data["trabajador_principal_manual"] = manual_match
            return nombre
        raise forms.ValidationError("Selecciona un trabajador válido del catálogo.")

    def clean(self):
        cleaned = super().clean()
        prefix_base = (self.prefix or "tramite_caso").replace("-", "_")
        _clear_optional_catalog_selection(
            self,
            cleaned,
            field_name="solicitante",
            search_keys=(
                f"{prefix_base}_solicitante_busqueda",
                "tramite_caso_solicitante_busqueda",
                "solicitante_busqueda",
            ),
        )
        _clear_optional_catalog_selection(
            self,
            cleaned,
            field_name="dirigido_a",
            search_keys=(
                f"{prefix_base}_destinatario_busqueda",
                "tramite_caso_destinatario_busqueda",
                "destinatario_busqueda",
            ),
        )
        adicionales_raw = cleaned.get("trabajadores_adicionales") or ""
        adicionales_data = _parse_json_value(adicionales_raw, [])
        adicionales_ids = []
        if isinstance(adicionales_data, list):
            for item in adicionales_data:
                if isinstance(item, dict):
                    raw_id = item.get("id") or item.get("pk")
                else:
                    raw_id = item
                if raw_id is None:
                    continue
                try:
                    adicionales_ids.append(int(raw_id))
                except (TypeError, ValueError):
                    continue
        cleaned["trabajadores_adicionales_ids"] = list(
            models.PlantillaEmpleado.objects.filter(id__in=adicionales_ids).values_list("id", flat=True)
        )

        centros_map_raw = cleaned.get("trabajadores_centros") or ""
        centros_map = _parse_json_value(centros_map_raw, {})
        if not isinstance(centros_map, dict):
            centros_map = {}
        cleaned["trabajadores_centros_map"] = {
            str(key): str(value)
            for key, value in centros_map.items()
            if value is not None and str(value).strip() != ""
        }

        principal = cleaned.get("trabajador_principal")
        if principal and principal.id in cleaned["trabajadores_adicionales_ids"]:
            cleaned["trabajadores_adicionales_ids"] = [
                pk for pk in cleaned["trabajadores_adicionales_ids"] if pk != principal.id
            ]
        has_primary_rango = bool(
            cleaned.get("incidencia_afiliacion")
            or cleaned.get("incidencia_fecha_inicio")
            or cleaned.get("incidencia_fecha_termino")
            or cleaned.get("incidencia_dias_otorgados") not in (None, "")
        )
        if not has_primary_rango:
            cleaned["incidencia_nombre_docente"] = ""
        elif not (cleaned.get("incidencia_nombre_docente") or "").strip():
            if principal:
                cleaned["incidencia_nombre_docente"] = principal.nombre
            else:
                cleaned["incidencia_nombre_docente"] = (
                    cleaned.get("trabajador_principal_nombre") or ""
                ).strip()
        cleaned["rangos_fechas_adicionales"] = _normalize_rangos_fechas(
            cleaned.get("rangos_fechas_adicionales") or []
        )
        cleaned["trabajadores_manuales_data"] = _normalize_manual_workers(
            cleaned.get("trabajadores_manuales") or ""
        )
        principal_manual = self.cleaned_data.get("trabajador_principal_manual")
        if not cleaned.get("trabajador_principal") and isinstance(principal_manual, dict):
            manual_match = next(
                (
                    item
                    for item in cleaned["trabajadores_manuales_data"]
                    if str(item.get("id") or "").strip()
                    == str(principal_manual.get("id") or "").strip()
                ),
                None,
            )
            if not manual_match:
                manual_match = _find_single_manual_worker_by_token(
                    cleaned["trabajadores_manuales_data"],
                    cleaned.get("trabajador_principal_nombre") or "",
                )
            if manual_match:
                cleaned["trabajador_principal_manual_data"] = manual_match
        cleaned = captura_guiada.validate_form_payload(
            self,
            cleaned,
            ambito=captura_guiada.AMBITO_TRAMITE,
            tipo_field="tipo",
            estatus_field="estatus",
            enforce_checklist_critical=False,
        )
        return cleaned

    def save_trabajadores(self, caso: models.CasoInterno) -> None:
        principal = self.cleaned_data.get("trabajador_principal")
        adicionales_ids = self.cleaned_data.get("trabajadores_adicionales_ids", [])
        centros_map = self.cleaned_data.get("trabajadores_centros_map", {})
        manuales = self.cleaned_data.get("trabajadores_manuales_data", [])
        manuales_persistidos = _persist_manual_workers(manuales)

        ids = set(adicionales_ids)
        if principal:
            ids.add(principal.id)
        ids.update(worker.id for worker in manuales_persistidos.values())

        if not principal:
            principal_manual = self.cleaned_data.get("trabajador_principal_manual_data")
            if isinstance(principal_manual, dict):
                principal_worker = manuales_persistidos.get(
                    str(principal_manual.get("id") or "").strip()
                )
                if principal_worker:
                    principal = principal_worker
                    ids.add(principal.id)

        existing = {
            rel.trabajador_id: rel
            for rel in models.CasoTrabajador.objects.filter(caso=caso)
        }

        for trabajador_id, rel in list(existing.items()):
            if trabajador_id not in ids:
                rel.delete()

        for trabajador_id in ids:
            rel = existing.get(trabajador_id)
            if not rel:
                rel = models.CasoTrabajador(caso=caso, trabajador_id=trabajador_id)
            rel.es_principal = bool(principal and trabajador_id == principal.id)
            codigo = ""
            if str(trabajador_id) in centros_map:
                codigo = centros_map.get(str(trabajador_id), "").strip()
            centro = None
            if codigo:
                centro = models.PlantillaCentroTrabajo.objects.filter(cct__iexact=codigo).first()
            rel.centro_trabajo_preferido = centro
            rel.save()

        manuales_restantes: list[dict[str, str]] = []
        if caso.trabajadores_manuales != manuales_restantes:
            caso.trabajadores_manuales = manuales_restantes
            caso.save(update_fields=["trabajadores_manuales", "actualizado_en"])


class HistorialEstatusTramiteCasoForm(forms.ModelForm):
    class Meta:
        model = models.HistorialEstatusTramiteCaso
        fields = ("estatus_nuevo", "fecha_estatus", "comentario")
        widgets = {
            "fecha_estatus": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "comentario": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estatus_nuevo"].queryset = models.EstatusTramite.objects.order_by("orden", "nombre")
        self.fields["estatus_nuevo"].required = False
        self.fields["estatus_nuevo"].widget.attrs.setdefault("class", "form-input")
        self.fields["fecha_estatus"].required = True
        self.fields["fecha_estatus"].widget.attrs.setdefault("class", "form-input")
        if not self.is_bound:
            initial_fecha = self.initial.get("fecha_estatus")
            if not initial_fecha and getattr(self.instance, "pk", None):
                initial_fecha = getattr(self.instance, "fecha_estatus_resuelta", None)
            self.fields["fecha_estatus"].initial = initial_fecha or timezone.localdate()
        self.fields["comentario"].widget.attrs.setdefault("class", "form-input")

    def clean(self):
        cleaned = super().clean()
        estatus = cleaned.get("estatus_nuevo")
        if estatus:
            return cleaned

        raw_terms = [
            self.data.get("tramite_estatus_busqueda"),
            self.data.get("tramite_estatus_edicion_busqueda"),
            self.data.get("estatus_busqueda"),
        ]
        term = ""
        for value in raw_terms:
            token = str(value or "").strip()
            if token:
                term = token
                break
        if term:
            queryset = self.fields["estatus_nuevo"].queryset
            resolved = queryset.filter(nombre__iexact=term).first()
            if not resolved:
                resolved = queryset.filter(nombre__icontains=term).order_by("orden", "nombre").first()
            if resolved:
                cleaned["estatus_nuevo"] = resolved
                return cleaned

        self.add_error("estatus_nuevo", "Selecciona un estatus de la lista.")
        return cleaned


class HistorialEstatusCasoForm(forms.ModelForm):
    class Meta:
        model = models.HistorialEstatusCaso
        fields = ("estatus_nuevo", "fecha_estatus", "comentario")
        widgets = {
            "fecha_estatus": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "comentario": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estatus_nuevo"].queryset = models.EstatusCaso.objects.order_by("orden", "nombre")
        self.fields["estatus_nuevo"].required = False
        self.fields["estatus_nuevo"].widget.attrs.setdefault("class", "form-input")
        self.fields["estatus_nuevo"].widget.attrs.setdefault("data-estatus-caso-select", "true")
        self.fields["estatus_nuevo"].widget.attrs.setdefault("data-estatus-api", "/api/estatus-caso/")
        self.fields["estatus_nuevo"].widget.attrs.setdefault("data-estatus-label", "estatus")
        self.fields["fecha_estatus"].required = True
        self.fields["fecha_estatus"].widget.attrs.setdefault("class", "form-input")
        if not self.is_bound:
            initial_fecha = self.initial.get("fecha_estatus")
            if not initial_fecha and getattr(self.instance, "pk", None):
                initial_fecha = getattr(self.instance, "fecha_estatus_resuelta", None)
            self.fields["fecha_estatus"].initial = initial_fecha or timezone.localdate()
        self.fields["comentario"].widget.attrs.setdefault("class", "form-input")

    def clean(self):
        cleaned = super().clean()
        estatus = cleaned.get("estatus_nuevo")
        if estatus:
            return cleaned

        raw_terms = [
            self.data.get("caso_estatus_busqueda"),
            self.data.get("caso_estatus_edicion_busqueda"),
            self.data.get("estatus_busqueda"),
        ]
        term = ""
        for value in raw_terms:
            token = str(value or "").strip()
            if token:
                term = token
                break
        if term:
            queryset = self.fields["estatus_nuevo"].queryset
            resolved = queryset.filter(nombre__iexact=term).first()
            if not resolved:
                resolved = queryset.filter(nombre__icontains=term).order_by("orden", "nombre").first()
            if resolved:
                cleaned["estatus_nuevo"] = resolved
                return cleaned

        self.add_error("estatus_nuevo", "Selecciona un estatus de la lista.")
        return cleaned


_MENTION_PATTERN = re.compile(r"(?<!\w)@([A-Za-z0-9._-]{3,150})")


class CasoComentarioInternoForm(forms.ModelForm):
    """Formulario para registrar comentarios internos en un expediente."""

    class Meta:
        model = models.CasoComentarioInterno
        fields = ("mensaje", "menciones")
        widgets = {
            "mensaje": forms.Textarea(attrs={"rows": 3}),
            "menciones": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        self.caso = kwargs.pop("caso", None)
        super().__init__(*args, **kwargs)
        if self.caso is None:
            raise ValueError("CasoComentarioInternoForm requiere un caso.")
        usuarios_qs = self.caso.usuarios_involucrados.filter(is_active=True).order_by(
            "first_name",
            "last_name",
            "username",
        )
        self._usuarios_mencionables = list(usuarios_qs)
        self._usuarios_por_username = {
            (usuario.username or "").strip().lower(): usuario
            for usuario in self._usuarios_mencionables
            if (usuario.username or "").strip()
        }
        self.fields["menciones"].queryset = usuarios_qs
        self.fields["menciones"].required = False
        self.fields["menciones"].help_text = (
            "Puedes mencionar escribiendo @usuario o seleccionando personas del expediente."
        )
        self.fields["menciones"].label_from_instance = (
            lambda user: f"{user.get_full_name() or user.username} (@{user.username})"
        )
        _add_css_class(self.fields["mensaje"].widget, "form-input")
        self.fields["mensaje"].widget.attrs.setdefault("placeholder", "Escribe un comentario interno")
        self.fields["mensaje"].widget.attrs.setdefault("maxlength", "3000")

    def clean_mensaje(self) -> str:
        mensaje = (self.cleaned_data.get("mensaje") or "").strip()
        if not mensaje:
            raise forms.ValidationError("Escribe un comentario para continuar.")
        return mensaje

    def clean(self):
        cleaned = super().clean()
        mensaje = cleaned.get("mensaje") or ""
        menciones_explicitas = list(cleaned.get("menciones") or [])
        usuarios_mencionados = {usuario.pk: usuario for usuario in menciones_explicitas}

        usernames_mencionados = {
            match.group(1).strip().lower()
            for match in _MENTION_PATTERN.finditer(mensaje)
            if (match.group(1) or "").strip()
        }
        invalidas = sorted(
            f"@{username}"
            for username in usernames_mencionados
            if username not in self._usuarios_por_username
        )
        if invalidas:
            raise forms.ValidationError(
                "Menciones no autorizadas para este expediente: %s."
                % ", ".join(invalidas)
            )
        for username in usernames_mencionados:
            usuario = self._usuarios_por_username.get(username)
            if usuario is not None:
                usuarios_mencionados[usuario.pk] = usuario
        cleaned["menciones_resueltas"] = list(usuarios_mencionados.values())
        return cleaned

    def save(self, *, caso: models.CasoInterno, autor=None) -> models.CasoComentarioInterno:
        if caso.pk != self.caso.pk:
            raise ValueError("El caso del formulario no coincide con el caso recibido.")
        actor = autor if getattr(autor, "is_authenticated", False) else None
        comentario = models.CasoComentarioInterno.objects.create(
            caso=caso,
            autor=actor,
            mensaje=self.cleaned_data["mensaje"],
        )
        menciones = self.cleaned_data.get("menciones_resueltas") or []
        if menciones:
            comentario.menciones.set(menciones)
        return comentario


class CasoTareaInternaForm(forms.ModelForm):
    """Formulario para registrar tareas/acuerdos internos del expediente."""

    class Meta:
        model = models.CasoTareaInterna
        fields = ("titulo", "descripcion", "responsable", "fecha_compromiso")
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2}),
            "fecha_compromiso": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.caso = kwargs.pop("caso", None)
        super().__init__(*args, **kwargs)
        if self.caso is None:
            raise ValueError("CasoTareaInternaForm requiere un caso.")
        usuarios_qs = self.caso.usuarios_involucrados.filter(is_active=True).order_by(
            "first_name",
            "last_name",
            "username",
        )
        self.fields["responsable"].queryset = usuarios_qs
        self.fields["responsable"].required = True
        self.fields["responsable"].label_from_instance = (
            lambda user: f"{user.get_full_name() or user.username} (@{user.username})"
        )
        for field in self.fields.values():
            _add_css_class(field.widget, "form-input")
        self.fields["titulo"].widget.attrs.setdefault("placeholder", "Ej. Integrar documentos faltantes")
        self.fields["fecha_compromiso"].widget.attrs.setdefault(
            "min",
            timezone.localdate().isoformat(),
        )

    def clean_titulo(self) -> str:
        titulo = (self.cleaned_data.get("titulo") or "").strip()
        if not titulo:
            raise forms.ValidationError("Captura un título para la tarea.")
        return titulo

    def clean_descripcion(self) -> str:
        return (self.cleaned_data.get("descripcion") or "").strip()

    def save(self, *, caso: models.CasoInterno, creador=None) -> models.CasoTareaInterna:
        if caso.pk != self.caso.pk:
            raise ValueError("El caso del formulario no coincide con el caso recibido.")
        actor = creador if getattr(creador, "is_authenticated", False) else None
        return models.CasoTareaInterna.objects.create(
            caso=caso,
            titulo=self.cleaned_data["titulo"],
            descripcion=self.cleaned_data.get("descripcion") or "",
            responsable=self.cleaned_data.get("responsable"),
            fecha_compromiso=self.cleaned_data["fecha_compromiso"],
            creada_por=actor,
            estado=models.CasoTareaInterna.ESTADO_PENDIENTE,
        )


def _get_latest_registro(empleado: models.PlantillaEmpleado):
    return (
        models.PlantillaRegistro.objects.filter(empleado=empleado)
        .select_related("centro_trabajo")
        .order_by("-anio", "-ciclo")
        .first()
    )


class PlantillaEmpleadoReferenceFormMixin(forms.ModelForm):
    """Mixin para seleccionar un trabajador desde la plantilla."""

    trabajador_nombre = forms.CharField(
        label="Nombre del trabajador",
        help_text="Busca por nombre, RFC o CURP para autocompletar la información.",
    )
    trabajador_field_name = "trabajador"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trabajador_field = self.fields.get(self.trabajador_field_name)
        if not trabajador_field:
            raise ValueError(
                "El formulario debe definir el campo trabajador para usar PlantillaEmpleadoReferenceFormMixin."
            )
        trabajador_field.queryset = models.PlantillaEmpleado.objects.order_by("nombre")
        trabajador_field.widget = forms.HiddenInput()
        trabajador_field.required = True

        nombre_field = self.fields["trabajador_nombre"]
        nombre_field.widget.attrs.setdefault(
            "placeholder", "Escribe el nombre, RFC o CURP del trabajador"
        )
        if self.instance and getattr(self.instance, "trabajador_id", None):
            nombre_field.initial = self.instance.trabajador.nombre

    def clean_trabajador_nombre(self) -> str:
        nombre = (self.cleaned_data.get("trabajador_nombre") or "").strip()
        trabajador = self.cleaned_data.get(self.trabajador_field_name)
        if trabajador:
            return nombre
        if not nombre:
            raise forms.ValidationError("Debes seleccionar un trabajador válido.")
        matches = models.PlantillaEmpleado.objects.filter(nombre__iexact=nombre)
        if matches.count() == 1:
            self.cleaned_data[self.trabajador_field_name] = matches.first()
            return nombre
        raise forms.ValidationError("Selecciona un trabajador válido del catálogo.")

    def clean(self):
        cleaned = super().clean()
        trabajador = cleaned.get(self.trabajador_field_name)
        if trabajador:
            correo = cleaned.get("trabajador_correo") or trabajador.correo
            celular = cleaned.get("trabajador_celular") or trabajador.celular
            sistema = cleaned.get("trabajador_sistema")
            if not sistema:
                registro = _get_latest_registro(trabajador)
                if registro and registro.centro_trabajo:
                    sistema = normalise_sistema(registro.centro_trabajo.sostenimiento)
            cleaned["trabajador_correo"] = correo or ""
            cleaned["trabajador_celular"] = celular or ""
            cleaned["trabajador_sistema"] = normalise_sistema(sistema or "")
        return cleaned


class PlantillaEmpleadoForm(forms.ModelForm):
    """Formulario para CRUD de trabajadores."""

    class Meta:
        model = models.PlantillaEmpleado
        fields = (
            "nombre",
            "rfc",
            "curp",
            "correo",
            "telefono",
            "celular",
            "direccion",
            "colonia",
            "codigo_postal",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            _add_css_class(field.widget, "form-input")


class LicenciaRegistroForm(PlantillaEmpleadoReferenceFormMixin):
    """Formulario principal para registrar licencias."""

    class Meta:
        model = models.LicenciaRegistro
        fields = (
            "trabajador",
            "trabajador_nombre",
            "trabajador_correo",
            "trabajador_celular",
            "trabajador_sistema",
            "tipo_tramite",
            "tipo_prorroga",
            "sindicato",
            "fecha_tramite",
            "numero_expediente",
            "respuesta_oficio",
            "respuesta_numero_expediente",
            "respuesta_fecha_recepcion",
            "visto_bueno",
            "visto_bueno_numero_expediente",
            "visto_bueno_fecha",
            "fecha_recepcion_daf",
            "aplica_estatal",
            "cita_valoracion",
            "cita_valoracion_numero_expediente",
            "cita_valoracion_fecha",
            "fecha_contacto",
            "dictamen_numero_expediente",
            "dictamen_fecha",
            "dictamen_periodo_de",
            "dictamen_periodo_hasta",
            "notificacion_numero_expediente",
            "notificacion_fecha",
            "estatus",
        )
        widgets = {
            "fecha_tramite": forms.DateInput(attrs={"type": "date"}),
            "respuesta_fecha_recepcion": forms.DateInput(attrs={"type": "date"}),
            "visto_bueno_fecha": forms.DateInput(attrs={"type": "date"}),
            "fecha_recepcion_daf": forms.DateInput(attrs={"type": "date"}),
            "cita_valoracion_fecha": forms.DateInput(attrs={"type": "date"}),
            "fecha_contacto": forms.DateInput(attrs={"type": "date"}),
            "dictamen_fecha": forms.DateInput(attrs={"type": "date"}),
            "dictamen_periodo_de": forms.DateInput(attrs={"type": "date"}),
            "dictamen_periodo_hasta": forms.DateInput(attrs={"type": "date"}),
            "notificacion_fecha": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["trabajador_correo"].required = False
        self.fields["trabajador_celular"].required = False
        self.fields["trabajador_sistema"].required = False
        self.fields["trabajador_sistema"].label = "Federal/Estatal"
        self.fields["respuesta_oficio"].required = False
        self.fields["respuesta_numero_expediente"].required = False
        self.fields["respuesta_fecha_recepcion"].required = False
        self.fields["visto_bueno"].required = False
        self.fields["visto_bueno_numero_expediente"].required = False
        self.fields["visto_bueno_fecha"].required = False
        self.fields["fecha_recepcion_daf"].required = False
        self.fields["cita_valoracion"].required = False
        self.fields["cita_valoracion_numero_expediente"].required = False
        self.fields["cita_valoracion_fecha"].required = False
        self.fields["fecha_contacto"].required = False
        self.fields["dictamen_numero_expediente"].required = False
        self.fields["dictamen_fecha"].required = False
        self.fields["dictamen_periodo_de"].required = False
        self.fields["dictamen_periodo_hasta"].required = False
        self.fields["notificacion_numero_expediente"].required = False
        self.fields["notificacion_fecha"].required = False
        self.fields["estatus"].required = False
        self.fields["estatus"].queryset = models.EstatusLicencia.objects.order_by("orden", "nombre")
        self.fields["numero_expediente"].widget.attrs.setdefault(
            "list", "prefijo-oficio-options-licencias"
        )
        self.fields["respuesta_numero_expediente"].widget.attrs.setdefault(
            "list", "prefijo-oficio-options-licencias"
        )
        self.fields["visto_bueno_numero_expediente"].widget.attrs.setdefault(
            "list", "prefijo-oficio-options-licencias"
        )
        self.fields["cita_valoracion_numero_expediente"].widget.attrs.setdefault(
            "list", "prefijo-oficio-options-licencias"
        )
        self.fields["dictamen_numero_expediente"].widget.attrs.setdefault(
            "list", "prefijo-oficio-options-licencias"
        )
        self.fields["notificacion_numero_expediente"].widget.attrs.setdefault(
            "list", "prefijo-oficio-options-licencias"
        )
        for name, field in self.fields.items():
            if name in {"trabajador", "trabajador_nombre"}:
                continue
            _add_css_class(field.widget, "form-input")
        _add_css_class(self.fields["trabajador_nombre"].widget, "form-input")


class HistorialEstatusLicenciaForm(forms.ModelForm):
    """Formulario para registrar cambios de estatus en licencias."""

    class Meta:
        model = models.HistorialEstatusLicencia
        fields = ("estatus_nuevo", "comentario")
        widgets = {"comentario": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estatus_nuevo"].queryset = models.EstatusLicencia.objects.order_by("orden", "nombre")
        for name, field in self.fields.items():
            _add_css_class(field.widget, "form-input")


class BulkTramiteCasoForm(TramiteCasoForm):
    """Formulario completo para agregar un trámite asociado a varios casos."""

    comentario_estatus = forms.CharField(
        label="Comentario de estatus",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    class Meta(TramiteCasoForm.Meta):
        pass


class BulkEstatusCasoForm(forms.Form):
    """Formulario para agregar un estatus a varios casos."""

    estatus_nuevo = forms.ModelChoiceField(
        queryset=models.EstatusCaso.objects.order_by("orden", "nombre"),
        label="Estatus nuevo",
    )
    comentario = forms.CharField(
        label="Comentario",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )


class FiltroGuardadoOperacionForm(forms.Form):
    """Formulario para crear filtros guardados de la operación diaria."""

    nombre = forms.CharField(
        label="Nombre del filtro",
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ej. Pendientes de hoy"}),
    )
    alcance = forms.ChoiceField(
        label="Alcance",
        choices=models.FiltroGuardadoUsuario.ALCANCE_CHOICES,
        initial=models.FiltroGuardadoUsuario.ALCANCE_CASOS_LISTADO,
        widget=forms.HiddenInput(),
    )
    querystring = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    def clean_querystring(self):
        querystring = (self.cleaned_data.get("querystring") or "").strip()
        if len(querystring) > 2000:
            raise forms.ValidationError("El filtro es demasiado largo.")
        return querystring


class OperacionAccionRapidaForm(forms.Form):
    """Valida acciones rápidas sobre casos y trámites en dashboard/cola."""

    ACTION_ASSIGN = "asignar"
    ACTION_STATUS = "cambiar_estatus"
    ACTION_CHOICES = (
        (ACTION_ASSIGN, "Asignar"),
        (ACTION_STATUS, "Cambiar estatus"),
    )
    TARGET_CASE = "caso"
    TARGET_TRAMITE = "tramite"
    TARGET_CHOICES = (
        (TARGET_CASE, "Caso"),
        (TARGET_TRAMITE, "Trámite"),
    )

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    target_type = forms.ChoiceField(choices=TARGET_CHOICES)
    target_id = forms.IntegerField(min_value=1)
    next = forms.CharField(required=False)
    usuario_asignado = forms.ModelChoiceField(
        queryset=get_user_model().objects.filter(is_active=True).order_by("username"),
        required=False,
    )
    estatus_caso = forms.ModelChoiceField(
        queryset=models.EstatusCaso.objects.order_by("orden", "nombre"),
        required=False,
    )
    estatus_tramite = forms.ModelChoiceField(
        queryset=models.EstatusTramite.objects.order_by("orden", "nombre"),
        required=False,
    )
    comentario = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("action")
        target_type = cleaned.get("target_type")
        if action == self.ACTION_ASSIGN and cleaned.get("usuario_asignado") is None:
            raise forms.ValidationError("Selecciona el usuario a asignar.")
        if action == self.ACTION_STATUS:
            if target_type == self.TARGET_CASE and cleaned.get("estatus_caso") is None:
                raise forms.ValidationError("Selecciona el estatus de caso.")
            if target_type == self.TARGET_TRAMITE and cleaned.get("estatus_tramite") is None:
                raise forms.ValidationError("Selecciona el estatus de trámite.")
        return cleaned


class ConvertirCasoAAnexoForm(forms.Form):
    caso_destino = forms.ModelChoiceField(
        queryset=models.CasoInterno.objects.all(),
        label="Caso destino",
    )
    mover_tramites_relacionados = forms.BooleanField(
        required=False,
        initial=True,
        label="Mover trámites anexos al caso destino",
    )
    eliminar_caso_origen = forms.BooleanField(
        required=False,
        initial=True,
        label="Eliminar caso origen (se convertirá en trámite anexo)",
    )
    confirmar_eliminacion = forms.BooleanField(
        required=False,
        label="Confirmo que deseo eliminar el caso origen después de convertirlo",
    )
    confirmacion_textual = forms.CharField(
        required=False,
        label="Confirmación textual",
        help_text="Escribe ELIMINAR para confirmar que deseas eliminar el caso origen.",
    )
    motivo = forms.CharField(
        required=False,
        label="Motivo de la conversión",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        caso_origen = kwargs.pop("caso_origen", None)
        super().__init__(*args, **kwargs)
        qs = models.CasoInterno.objects.all().order_by("-fecha_apertura", "-fecha_registro")
        if caso_origen:
            qs = qs.exclude(pk=caso_origen.pk)
        self.fields["caso_destino"].queryset = qs
        for field in self.fields.values():
            _add_css_class(field.widget, "form-input")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("eliminar_caso_origen"):
            if not cleaned.get("confirmar_eliminacion"):
                raise forms.ValidationError(
                    "Debes confirmar la eliminación del caso origen para continuar."
                )
            confirm_text = (cleaned.get("confirmacion_textual") or "").strip().upper()
            if confirm_text != "ELIMINAR":
                raise forms.ValidationError("Debes escribir ELIMINAR para confirmar la eliminación.")
        return cleaned


class ConvertirCasosAAnexoBulkForm(forms.Form):
    caso_destino = forms.ModelChoiceField(
        queryset=models.CasoInterno.objects.all(),
        label="Caso destino",
    )
    mover_tramites_relacionados = forms.BooleanField(
        required=False,
        initial=True,
        label="Mover trámites anexos al caso destino",
    )
    eliminar_caso_origen = forms.BooleanField(
        required=False,
        initial=True,
        label="Eliminar caso(s) origen (se convertirán en trámite anexo)",
    )
    confirmar_eliminacion = forms.BooleanField(
        required=False,
        label="Confirmo que deseo eliminar los casos origen después de convertirlos",
    )
    confirmacion_textual = forms.CharField(
        required=False,
        label="Confirmación textual",
        help_text="Escribe ELIMINAR para confirmar que deseas eliminar los casos origen.",
    )
    motivo = forms.CharField(
        required=False,
        label="Motivo de la conversión",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        excluded_ids = kwargs.pop("excluded_ids", None) or []
        super().__init__(*args, **kwargs)
        qs = models.CasoInterno.objects.all().order_by("-fecha_apertura", "-fecha_registro")
        if excluded_ids:
            qs = qs.exclude(pk__in=excluded_ids)
        self.fields["caso_destino"].queryset = qs
        for field in self.fields.values():
            _add_css_class(field.widget, "form-input")

    def clean_caso_destino(self):
        destino = self.cleaned_data.get("caso_destino")
        if not destino:
            raise forms.ValidationError("Selecciona un caso destino válido.")
        return destino

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("eliminar_caso_origen"):
            if not cleaned.get("confirmar_eliminacion"):
                raise forms.ValidationError(
                    "Debes confirmar la eliminación de los casos origen para continuar."
                )
            confirm_text = (cleaned.get("confirmacion_textual") or "").strip().upper()
            if confirm_text != "ELIMINAR":
                raise forms.ValidationError("Debes escribir ELIMINAR para confirmar la eliminación.")
        return cleaned

class PromoverTramiteACasoForm(forms.Form):
    estatus_caso = forms.ModelChoiceField(
        queryset=models.EstatusCaso.objects.order_by("orden", "nombre"),
        label="Estatus del caso",
    )
    tipo_inicial = forms.ModelChoiceField(
        queryset=models.TipoProceso.objects.order_by("nombre"),
        label="Tipo inicial",
    )
    fecha_apertura = forms.DateField(
        label="Fecha de apertura",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    mover_tramites_relacionados = forms.BooleanField(
        required=False,
        initial=True,
        label="Mover trámites anexos al nuevo caso",
    )
    mover_caso_actual_a_anexo = forms.BooleanField(
        required=False,
        initial=True,
        label="Convertir el caso actual en trámite anexo",
    )
    eliminar_caso_anterior = forms.BooleanField(
        required=False,
        initial=True,
        label="Eliminar el caso anterior después de la conversión",
    )

    def __init__(self, *args, **kwargs):
        tramite = kwargs.pop("tramite", None)
        super().__init__(*args, **kwargs)
        if tramite:
            self.fields["tipo_inicial"].initial = tramite.tipo_id
            self.fields["fecha_apertura"].initial = tramite.fecha
        for field in self.fields.values():
            _add_css_class(field.widget, "form-input")


class FolioRegistroForm(forms.ModelForm):
    prefijo = forms.ModelChoiceField(
        label="Prefijo",
        queryset=models.FolioPrefijo.objects.none(),
        empty_label="Selecciona un prefijo",
    )
    casos = forms.ModelMultipleChoiceField(
        label="Casos asociados",
        queryset=models.CasoInterno.objects.none(),
        required=False,
    )

    class Meta:
        model = models.FolioRegistro
        fields = ("prefijo", "tipo", "casos", "tramite", "notas")
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        cleaned = super().clean()
        casos = cleaned.get("casos")
        tramite = cleaned.get("tramite")
        tipo = cleaned.get("tipo")
        if casos:
            cleaned["tipo"] = "caso"
            cleaned["tramite"] = None
        elif tramite:
            cleaned["tipo"] = "tramite"
            cleaned["casos"] = models.CasoInterno.objects.none()
        tipo = cleaned.get("tipo")
        if tipo == "caso":
            if not cleaned.get("casos"):
                self.add_error("casos", "Selecciona al menos un caso asociado.")
        elif tipo == "tramite":
            if not cleaned.get("tramite"):
                self.add_error("tramite", "Selecciona el trámite asociado.")
        else:
            if not casos and not tramite:
                self.add_error("casos", "Selecciona al menos un caso o un trámite.")
                self.add_error("tramite", "Selecciona un caso o un trámite.")
        casos = cleaned.get("casos")
        tramite = cleaned.get("tramite")
        if casos and tramite:
            self.add_error("casos", "Selecciona casos o trámite, no ambos.")
            self.add_error("tramite", "Selecciona solo un caso o un trámite.")
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["prefijo"] = forms.CharField(
                label="Prefijo",
                required=False,
                initial=self.instance.prefijo or "",
                disabled=True,
            )
        else:
            self.fields["prefijo"].queryset = (
                models.FolioPrefijo.objects.filter(esta_activo=True).order_by("nombre")
            )
            self.fields["prefijo"].label_from_instance = (
                lambda p: f"{p.nombre} · {p.descripcion}" if p.descripcion else p.nombre
            )
        if "tipo" in self.fields:
            self.fields["tipo"].widget = forms.HiddenInput()
        if "casos" in self.fields:
            if self.is_bound:
                ids = []
                data = getattr(self, "data", None)
                if data is not None:
                    if hasattr(data, "getlist"):
                        ids = data.getlist("casos")
                    else:
                        value = data.get("casos", [])
                        ids = value if isinstance(value, (list, tuple)) else [value]
                self.fields["casos"].queryset = models.CasoInterno.objects.filter(pk__in=ids)
            elif self.instance.pk:
                self.fields["casos"].queryset = self.instance.casos.all()
            else:
                self.fields["casos"].queryset = models.CasoInterno.objects.none()
        if self.instance.pk:
            for name in ("prefijo",):
                if name in self.fields:
                    self.fields[name].disabled = True
        for field in self.fields.values():
            _add_css_class(field.widget, "form-input")
