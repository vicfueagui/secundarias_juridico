"""Formularios para el registro y seguimiento de trámites."""
from __future__ import annotations

from django import forms

from tramites import models
from tramites.utils import normalise_sistema


def _add_css_class(widget: forms.Widget, classname: str) -> None:
    clases = widget.attrs.get("class", "").split()
    if classname not in clases:
        clases.append(classname)
    widget.attrs["class"] = " ".join(filter(None, clases))


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
        cct_field.queryset = models.CCTSecundaria.objects.order_by("cct")
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

    def get_default_cct(self) -> models.CCTSecundaria | None:
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
            cct_obj = models.CCTSecundaria.objects.get(cct__iexact=codigo)
        except models.CCTSecundaria.DoesNotExist as exc:
            raise forms.ValidationError("No se encontró el CCT en el catálogo.") from exc
        self.cleaned_data[self.cct_field_name] = cct_obj
        self.instance.cct = cct_obj
        self._apply_cct_data(cct_obj)
        return codigo

    def _apply_cct_data(self, cct_obj: models.CCTSecundaria) -> None:
        if self.cct_nombre_field and self.cct_nombre_field in self.cleaned_data:
            self.cleaned_data[self.cct_nombre_field] = cct_obj.nombre
        if self.cct_sistema_field and self.cct_sistema_field in self.cleaned_data:
            self.cleaned_data[self.cct_sistema_field] = normalise_sistema(cct_obj.sostenimiento)
        if self.cct_modalidad_field and self.cct_modalidad_field in self.cleaned_data:
            self.cleaned_data[self.cct_modalidad_field] = cct_obj.servicio or ""
        if (
            self.cct_asesor_field
            and self.cct_asesor_field in self.cleaned_data
            and not self.cleaned_data.get(self.cct_asesor_field)
        ):
            self.cleaned_data[self.cct_asesor_field] = cct_obj.asesor or ""

    def clean(self):
        cleaned = super().clean()
        cct_obj = cleaned.get(self.cct_field_name) or getattr(self.instance, "cct", None)
        if cct_obj:
            self.instance.cct = cct_obj
            if self.cct_nombre_field and self.cct_nombre_field in cleaned:
                cleaned[self.cct_nombre_field] = cleaned.get(self.cct_nombre_field) or cct_obj.nombre
            if self.cct_sistema_field and self.cct_sistema_field in cleaned:
                cleaned[self.cct_sistema_field] = normalise_sistema(
                    cleaned.get(self.cct_sistema_field) or cct_obj.sostenimiento
                )
            if self.cct_modalidad_field and self.cct_modalidad_field in cleaned:
                cleaned[self.cct_modalidad_field] = cleaned.get(self.cct_modalidad_field) or (cct_obj.servicio or "")
            if self.cct_asesor_field and self.cct_asesor_field in cleaned and not cleaned.get(self.cct_asesor_field):
                cleaned[self.cct_asesor_field] = cct_obj.asesor or ""
        return cleaned


class CasoInternoForm(CCTReferenceFormMixin):
    """Formulario principal para registrar trámites."""

    class Meta:
        model = models.CasoInterno
        fields = (
            "cct",
            "cct_nombre",
            "cct_sistema",
            "cct_modalidad",
            "asesor_cct",
            "fecha_apertura",
            "estatus",
            "tipo_inicial",
            "tipo_violencia",
            "asunto",
            "numero_oficio",
            "solicitante",
            "dirigido_a",
            "generador_nombre",
            "generador_iniciales",
            "generador_sexo",
            "receptor_nombre",
            "receptor_iniciales",
            "receptor_sexo",
            "receptores_adicionales",
            "observaciones_iniciales",
        )
        widgets = {
            "fecha_apertura": forms.DateInput(attrs={"type": "date"}),
            "asunto": forms.Textarea(attrs={"rows": 3}),
            "observaciones_iniciales": forms.Textarea(attrs={"rows": 3}),
            "receptores_adicionales": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estatus"].queryset = models.EstatusCaso.objects.order_by("orden", "nombre")
        self.fields["tipo_inicial"].queryset = models.TipoProceso.objects.order_by("nombre")
        self.fields["fecha_apertura"].label = "Fecha del trámite"
        self.fields["numero_oficio"].widget.attrs.setdefault(
            "placeholder", "Ej. SE/SEB/DES-EESP/001/2024"
        )
        self.fields["numero_oficio"].widget.attrs.setdefault("list", "prefijo-oficio-options")
        self.fields["tipo_violencia"].required = False
        self.fields["tipo_violencia"].queryset = models.TipoViolencia.objects.order_by("nombre")
        self.fields["solicitante"].required = False
        self.fields["solicitante"].queryset = models.Solicitante.objects.order_by("nombre")
        self.fields["dirigido_a"].required = False
        self.fields["dirigido_a"].queryset = models.Destinatario.objects.order_by("nombre")
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
        ):
            self.fields[optional_field].required = False
        for name, field in self.fields.items():
            if name in {"cct", "cct_codigo"}:
                continue
            _add_css_class(field.widget, "form-input")
        _add_css_class(self.fields["cct_codigo"].widget, "form-input")
        self.order_fields(
            [
                "cct",
                "cct_codigo",
                "cct_nombre",
                "cct_sistema",
                "cct_modalidad",
                "asesor_cct",
                "tipo_inicial",
                "fecha_apertura",
                "tipo_violencia",
                "asunto",
                "numero_oficio",
                "solicitante",
                "dirigido_a",
                "generador_nombre",
                "generador_iniciales",
                "generador_sexo",
                "receptor_nombre",
                "receptor_iniciales",
                "receptor_sexo",
                "receptores_adicionales",
                "observaciones_iniciales",
                "estatus",
            ]
        )


class TramiteCasoForm(forms.ModelForm):
    class Meta:
        model = models.TramiteCaso
        fields = (
            "tipo",
            "estatus",
            "fecha",
            "numero_oficio",
            "tipo_violencia",
            "asunto",
            "solicitante",
            "dirigido_a",
            "observaciones",
            "generador_nombre",
            "generador_iniciales",
            "generador_sexo",
            "receptor_nombre",
            "receptor_iniciales",
            "receptor_sexo",
            "receptores_adicionales",
        )
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
            "receptores_adicionales": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].queryset = models.TipoProceso.objects.order_by("nombre")
        self.fields["estatus"].queryset = models.EstatusTramite.objects.order_by("orden", "nombre")
        self.fields["estatus"].widget.attrs.setdefault("data-estatus-api", "/api/estatus-tramite/")
        self.fields["estatus"].widget.attrs.setdefault("data-estatus-label", "estatus de trámite")
        self.fields["tipo_violencia"].queryset = models.TipoViolencia.objects.order_by("nombre")
        self.fields["tipo_violencia"].required = False
        self.fields["solicitante"].queryset = models.Solicitante.objects.order_by("nombre")
        self.fields["solicitante"].required = False
        self.fields["dirigido_a"].queryset = models.Destinatario.objects.order_by("nombre")
        self.fields["dirigido_a"].required = False
        self.fields["numero_oficio"].widget.attrs.setdefault("list", "prefijo-oficio-options")
        sexo_choices = models.SEXO_NNA_CHOICES
        for field_name in ("generador_sexo", "receptor_sexo"):
            self.fields[field_name].required = False
            self.fields[field_name].choices = [("", "---------")] + list(sexo_choices)
        for optional_field in (
            "generador_nombre",
            "generador_iniciales",
            "receptor_nombre",
            "receptor_iniciales",
        ):
            self.fields[optional_field].required = False
        for name, field in self.fields.items():
            _add_css_class(field.widget, "form-input")
        self.fields["numero_oficio"].widget.attrs.setdefault("placeholder", "Ej. SE/SEB/DES-EESP/001/2024")
        self.fields["asunto"].widget.attrs.setdefault("placeholder", "Descripción breve del trámite asociado.")


class HistorialEstatusTramiteCasoForm(forms.ModelForm):
    class Meta:
        model = models.HistorialEstatusTramiteCaso
        fields = ("estatus_nuevo", "comentario")
        widgets = {"comentario": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estatus_nuevo"].queryset = models.EstatusTramite.objects.order_by("orden", "nombre")
        self.fields["estatus_nuevo"].widget.attrs.setdefault("class", "form-input")
        self.fields["comentario"].widget.attrs.setdefault("class", "form-input")


class HistorialEstatusCasoForm(forms.ModelForm):
    class Meta:
        model = models.HistorialEstatusCaso
        fields = ("estatus_nuevo", "comentario")
        widgets = {"comentario": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estatus_nuevo"].queryset = models.EstatusCaso.objects.order_by("orden", "nombre")
        self.fields["estatus_nuevo"].widget.attrs.setdefault("class", "form-input")
        self.fields["comentario"].widget.attrs.setdefault("class", "form-input")
