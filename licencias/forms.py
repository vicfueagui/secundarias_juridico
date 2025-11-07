"""Formularios web para licencias."""
from __future__ import annotations

from datetime import date
from typing import Any

from django import forms
from django.db.models import Case, IntegerField, When

from licencias import models
from licencias.utils import normalise_sistema
from licencias.services import validators


class TramiteForm(forms.ModelForm):
    TIPO_TRAMITE_OPCIONES: tuple[tuple[str, str], ...] = (
        ("Licencia 754", "Licencia 754"),
        ("70 BIS", "70 BIS"),
        ("Cambio de Función", "Cambio de Función"),
        ("Cambio de actividad", "Cambio de actividad"),
        ("Otro", "Otro"),
    )
    SUBSISTEMA_OPCIONES: tuple[tuple[str, str], ...] = (
        ("Federal", "Federal"),
        ("Estatal", "Estatal"),
    )
    SINDICATO_OPCIONES: tuple[tuple[str, str], ...] = (
        ("SYTTE", "SYTTE"),
        ("SNTE sección 33", "SNTE sección 33"),
        ("SNTE sección 57", "SNTE sección 57"),
        ("SETEY", "SETEY"),
        ("GNTE", "GNTE"),
    )
    TIPO_SOLICITUD_CHOICES: tuple[tuple[str, str], ...] = (
        (models.Tramite.TipoSolicitud.INICIAL, "Inicial"),
        (models.Tramite.TipoSolicitud.PRIMERA_PRORROGA, "Primera prórroga"),
        (models.Tramite.TipoSolicitud.SEGUNDA_PRORROGA, "Segunda prórroga"),
        (models.Tramite.TipoSolicitud.TERCERA_PRORROGA, "Tercera prórroga"),
        (models.Tramite.TipoSolicitud.CUARTA_PRORROGA, "Cuarta prórroga"),
        (models.Tramite.TipoSolicitud.QUINTA_PRORROGA, "Quinta prórroga"),
        (models.Tramite.TipoSolicitud.SEXTA_PRORROGA, "Sexta prórroga"),
        (models.Tramite.TipoSolicitud.SEPTIMA_PRORROGA, "Séptima prórroga"),
        (models.Tramite.TipoSolicitud.OCTAVA_PRORROGA, "Octava prórroga"),
        (models.Tramite.TipoSolicitud.DESCONOCIDO, "Otro"),
    )

    class Meta:
        model = models.Tramite
        fields = (
            # Sección 1: Nivel Educativo
            "tipo_tramite",
            "subsistema",
            "tramite_inicial_o_prorroga",
            "trabajador_nombre",
            "diagnostico",
            "sindicato",
            "contacto",
            "oficio_origen_num",
            "fecha_recepcion_nivel",
            "incidencias_integracion",
            "oficio_envio_subsecretaria",
            "fecha_recepcion_subsecretaria",
            # Sección 2: SEB/DEP. Asesoría Técnica
            "incidencias_vobo",
            "vobo_num_y_fecha",
            "fecha_recepcion_daf",
            # Sección 3: Trámites Estatales
            "fecha_cita_valoracion",
            "fecha_contacto_cita",
            "incidencias_contacto_cita",
            # Sección 4: Nivel Educativo (Dictamen)
            "oficio_dictamen_num",
            "fecha_dictamen",
            "autorizado",
            "periodo_autorizado",
            "oficio_notificacion",
            "fecha_notificacion",
            # Sección 5: Prórrogas
            "prorroga1_oficio_origen",
            "prorroga1_fecha_ingreso",
            "prorroga1_incidencia",
            "prorroga1_oficio_envio_daf",
            "prorroga1_fecha_recepcion_daf",
            "prorroga1_fecha_cita",
            "prorroga1_fecha_contacto",
            "prorroga1_oficio_dictamen",
            "prorroga1_fecha_dictamen",
            "prorroga1_autorizado",
            "prorroga1_periodo",
            "prorroga1_oficio_notificacion",
            "prorroga1_fecha_notificacion",
            "prorroga2_oficio_origen",
            "prorroga2_fecha_ingreso",
            "prorroga2_incidencia",
            "prorroga2_oficio_envio_daf",
            "prorroga2_fecha_recepcion_daf",
            "prorroga2_fecha_cita",
            "prorroga2_fecha_contacto",
            "prorroga2_oficio_dictamen",
            "prorroga2_fecha_dictamen",
            "prorroga2_autorizado",
            "prorroga2_periodo",
            "prorroga2_oficio_notificacion",
            "prorroga2_fecha_notificacion",
            # Campos generales
            "estado_actual",
            "user_responsable",
            "observaciones",
        )
        widgets = {
            "fecha_recepcion_nivel": forms.DateInput(attrs={"type": "date"}),
            "fecha_recepcion_subsecretaria": forms.DateInput(attrs={"type": "date"}),
            "fecha_recepcion_daf": forms.DateInput(attrs={"type": "date"}),
            "fecha_cita_valoracion": forms.DateInput(attrs={"type": "date"}),
            "fecha_contacto_cita": forms.DateInput(attrs={"type": "date"}),
            "fecha_dictamen": forms.DateInput(attrs={"type": "date"}),
            "fecha_notificacion": forms.DateInput(attrs={"type": "date"}),
            "prorroga1_fecha_ingreso": forms.DateInput(attrs={"type": "date"}),
            "prorroga1_fecha_recepcion_daf": forms.DateInput(attrs={"type": "date"}),
            "prorroga1_fecha_cita": forms.DateInput(attrs={"type": "date"}),
            "prorroga1_fecha_contacto": forms.DateInput(attrs={"type": "date"}),
            "prorroga1_fecha_dictamen": forms.DateInput(attrs={"type": "date"}),
            "prorroga1_fecha_notificacion": forms.DateInput(attrs={"type": "date"}),
            "prorroga2_fecha_ingreso": forms.DateInput(attrs={"type": "date"}),
            "prorroga2_fecha_recepcion_daf": forms.DateInput(attrs={"type": "date"}),
            "prorroga2_fecha_cita": forms.DateInput(attrs={"type": "date"}),
            "prorroga2_fecha_contacto": forms.DateInput(attrs={"type": "date"}),
            "prorroga2_fecha_dictamen": forms.DateInput(attrs={"type": "date"}),
            "prorroga2_fecha_notificacion": forms.DateInput(attrs={"type": "date"}),
            "incidencias_integracion": forms.Textarea(attrs={"rows": 3}),
            "incidencias_vobo": forms.Textarea(attrs={"rows": 3}),
            "incidencias_contacto_cita": forms.Textarea(attrs={"rows": 3}),
            "prorroga1_incidencia": forms.Textarea(attrs={"rows": 3}),
            "prorroga2_incidencia": forms.Textarea(attrs={"rows": 3}),
            "contacto": forms.Textarea(attrs={"rows": 3}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prepare_catalog_field(
            field_name="tipo_tramite",
            model_cls=models.TipoTramite,
            opciones=self.TIPO_TRAMITE_OPCIONES,
            empty_label="Selecciona licencia o trámite",
        )
        self._prepare_catalog_field(
            field_name="subsistema",
            model_cls=models.Subsistema,
            opciones=self.SUBSISTEMA_OPCIONES,
            empty_label="Selecciona una opción",
        )
        self._prepare_catalog_field(
            field_name="sindicato",
            model_cls=models.Sindicato,
            opciones=self.SINDICATO_OPCIONES,
            empty_label="Selecciona un sindicato",
        )
        self.fields["tramite_inicial_o_prorroga"].choices = self.TIPO_SOLICITUD_CHOICES
        self.fields["tramite_inicial_o_prorroga"].widget.attrs.setdefault(
            "aria-label", "Selecciona el tipo de trámite o prórroga"
        )
        for field in self.fields.values():
            self._append_css_class(field.widget, "form-input")
            if isinstance(field.widget, forms.DateInput):
                self._append_css_class(field.widget, "date-input")
                field.widget.attrs.setdefault("placeholder", "Selecciona la fecha")
        self.fields["diagnostico"].queryset = models.Diagnostico.objects.order_by("nombre")
        self.fields["diagnostico"].empty_label = "Selecciona un diagnóstico"
        self._configure_estado_actual()
        self._set_prorroga_labels()
        # Organizar campos por secciones para el template
        self.sections = {
            "seccion1": {
                "title": "SECCIÓN 1 / NIVEL EDUCATIVO",
                "fields": [
                    "tipo_tramite", "subsistema", "tramite_inicial_o_prorroga",
                    "trabajador_nombre", "diagnostico", "sindicato", "contacto",
                    "oficio_origen_num", "fecha_recepcion_nivel", "incidencias_integracion",
                    "oficio_envio_subsecretaria", "fecha_recepcion_subsecretaria"
                ]
            },
            "seccion2": {
                "title": "SECCIÓN 2 / SEB/DEP. ASESORÍA TÉCNICA Y GESTIÓN DE LA INFORMACIÓN",
                "fields": [
                    "incidencias_vobo", "vobo_num_y_fecha", "fecha_recepcion_daf"
                ]
            },
            "seccion3": {
                "title": "SECCIÓN 3 / APLICA PARA TRÁMITES ESTATALES/NIVEL EDUCATIVO y Prórrogas",
                "fields": [
                    "fecha_cita_valoracion", "fecha_contacto_cita", "incidencias_contacto_cita"
                ]
            },
            "seccion4": {
                "title": "SECCIÓN 4 / NIVEL EDUCATIVO",
                "fields": [
                    "oficio_dictamen_num", "fecha_dictamen", "autorizado",
                    "periodo_autorizado", "oficio_notificacion", "fecha_notificacion"
                ]
            },
            "seccion5": {
                "title": "SECCIÓN 5 / PRÓRROGAS/NIVEL EDUCATIVO",
                "subsections": [
                    {
                        "subtitle": "Primera Prórroga",
                        "fields": [
                            "prorroga1_oficio_origen", "prorroga1_fecha_ingreso", "prorroga1_incidencia",
                            "prorroga1_oficio_envio_daf", "prorroga1_fecha_recepcion_daf",
                            "prorroga1_fecha_cita", "prorroga1_fecha_contacto",
                            "prorroga1_oficio_dictamen", "prorroga1_fecha_dictamen",
                            "prorroga1_autorizado", "prorroga1_periodo",
                            "prorroga1_oficio_notificacion", "prorroga1_fecha_notificacion"
                        ]
                    },
                    {
                        "subtitle": "Segunda Prórroga",
                        "fields": [
                            "prorroga2_oficio_origen", "prorroga2_fecha_ingreso", "prorroga2_incidencia",
                            "prorroga2_oficio_envio_daf", "prorroga2_fecha_recepcion_daf",
                            "prorroga2_fecha_cita", "prorroga2_fecha_contacto",
                            "prorroga2_oficio_dictamen", "prorroga2_fecha_dictamen",
                            "prorroga2_autorizado", "prorroga2_periodo",
                            "prorroga2_oficio_notificacion", "prorroga2_fecha_notificacion"
                        ]
                    }
                ]
            },
            "general": {
                "title": "INFORMACIÓN GENERAL",
                "fields": ["estado_actual", "user_responsable", "observaciones"]
            }
        }

    def _set_prorroga_labels(self) -> None:
        """Actualiza los labels de la sección de prórrogas."""
        base_labels = {
            "oficio_origen": "Número de oficio del sindicato o escrito de origen",
            "fecha_ingreso": "Fecha de ingreso al nivel educativo",
            "incidencia": "Incidencia en la prórroga",
            "oficio_envio_daf": "Número de oficio de envío a la Subd. de Org. y Adm. de Personal -DAF",
            "fecha_recepcion_daf": "Fecha de recepción por la Subd. de Org. y Adm. de Personal -DAF",
            "fecha_cita": "Fecha de la cita de valoración del trabajador (TRÁMITES ESTATALES)",
            "fecha_contacto": "Fecha en la que se contactó al sindicato y al trabajador/señalar medio",
            "oficio_dictamen": "Número de oficio del Dictamen emitido por la Subd. de Org. y Adm. de Personal -DAF",
            "fecha_dictamen": "Fecha del dictamen",
            "autorizado": "Autorizado",
            "periodo": "Periodo",
            "oficio_notificacion": "Oficio de Notificación de la prórroga realizada al sindicato y al trabajador",
            "fecha_notificacion": "Fecha en la que se realizó la notificación al sindicato y al trabajador",
        }
        for numero in ("1", "2"):
            for suffix, label in base_labels.items():
                field_name = f"prorroga{numero}_{suffix}"
                if field_name in self.fields:
                    self.fields[field_name].label = label

    def _prepare_catalog_field(
        self,
        *,
        field_name: str,
        model_cls: type[models.CatalogoBase],
        opciones: tuple[tuple[str, str], ...],
        empty_label: str,
    ) -> None:
        nombres = [nombre for nombre, _ in opciones]
        existentes = {
            registro.nombre: registro
            for registro in model_cls.objects.filter(nombre__in=nombres)
        }
        for nombre in nombres:
            if nombre not in existentes:
                registro, _ = model_cls.objects.get_or_create(
                    nombre=nombre, defaults={"descripcion": nombre}
                )
                existentes[nombre] = registro
        order = Case(
            *[
                When(nombre=nombre, then=pos)
                for pos, nombre in enumerate(nombres)
            ],
            default=len(nombres),
            output_field=IntegerField(),
        )
        field = self.fields[field_name]
        field.queryset = model_cls.objects.filter(nombre__in=nombres).order_by(order, "nombre")
        field.empty_label = empty_label

    @staticmethod
    def _append_css_class(widget: forms.Widget, classname: str) -> None:
        clases = widget.attrs.get("class", "").split()
        if classname not in clases:
            clases.append(classname)
        widget.attrs["class"] = " ".join(filter(None, clases))

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        instance = self.instance or models.Tramite()
        for campo, valor in cleaned.items():
            setattr(instance, campo, valor)
        validators.validar_fechas_chronologicas(instance)
        validators.validar_campos_por_etapa(instance)
        if instance.pk:
            etapa_anterior = (
                models.Tramite.objects.filter(pk=instance.pk)
                .values_list("estado_actual", flat=True)
                .first()
            )
            if etapa_anterior:
                etapa_obj = models.Etapa.objects.filter(pk=etapa_anterior).first()
            else:
                etapa_obj = None
        else:
            etapa_obj = None
        validators.validar_transicion_etapa(etapa_obj, cleaned.get("estado_actual"))
        return cleaned

    def _configure_estado_actual(self) -> None:
        """Ordena las etapas y asigna una etapa inicial por defecto."""
        field = self.fields.get("estado_actual")
        if not field:
            return
        queryset = models.Etapa.objects.order_by("orden", "nombre")
        field.queryset = queryset
        field.empty_label = "Selecciona la etapa actual"
        if self.instance.pk or self.initial.get("estado_actual"):
            return
        etapa_inicial = queryset.filter(es_final=False).order_by("orden").first() or queryset.first()
        if etapa_inicial:
            field.initial = etapa_inicial.pk


class MovimientoForm(forms.ModelForm):
    class Meta:
        model = models.Movimiento
        fields = ("etapa_nueva", "comentario")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            TramiteForm._append_css_class(field.widget, "form-input")
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("rows", 3)


class ImportCSVForm(forms.Form):
    archivo = forms.FileField(help_text="Selecciona el archivo CSV exportado de Excel.")


class RelacionProtocoloForm(forms.ModelForm):
    cct_codigo = forms.CharField(
        label="CCT",
        max_length=12,
        help_text="Escribe la clave del centro de trabajo para autocompletar la información.",
    )

    TIPO_VIOLENCIA_SUGERIDAS: tuple[str, ...] = (
        "FAMILIAR",
        "ENTRE NNA",
        "EN LA COMUNIDAD",
        "INSTITUCIONAL",
        "OTRO (MENCIONAR)",
    )

    class Meta:
        model = models.RelacionProtocolo
        fields = (
            "numero_registro",
            "cct",
            "escuela",
            "anio",
            "fecha_inicio",
            "iniciales",
            "nombre_nna",
            "sexo",
            "asesor_juridico",
            "tipo_violencia",
            "descripcion",
            "comentarios",
            "estatus",
        )
        widgets = {
            "numero_registro": forms.HiddenInput(),
            "cct": forms.HiddenInput(),
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            "descripcion": forms.Textarea(attrs={"rows": 4}),
            "comentarios": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cct"].queryset = models.CCTSecundaria.objects.order_by("cct")
        self.fields["cct"].required = False
        self.fields["numero_registro"].required = False
        self.fields["escuela"].required = False
        self.fields["asesor_juridico"].required = False

        self.fields["cct_codigo"].widget.attrs.setdefault("list", "cct-options")
        self.fields["cct_codigo"].widget.attrs.setdefault("placeholder", "Ej. 31EES0001H")
        self.fields["cct_codigo"].widget.attrs.setdefault("autocomplete", "off")
        if self.instance and self.instance.cct_id:
            self.fields["cct_codigo"].initial = self.instance.cct_id

        escuela_widget = self.fields["escuela"].widget
        escuela_widget.attrs.setdefault(
            "placeholder", "Se llenará automáticamente según el CCT seleccionado."
        )
        escuela_widget.attrs.setdefault("readonly", "readonly")
        escuela_widget.attrs.setdefault("id", "id_cct_nombre")

        asesor_widget = self.fields["asesor_juridico"].widget
        asesor_widget.attrs.setdefault(
            "placeholder", "Se llenará automáticamente según el CCT seleccionado."
        )
        asesor_widget.attrs.setdefault("readonly", "readonly")
        asesor_widget.attrs.setdefault("id", "id_asesor")
        self.fields["asesor_juridico"].label = "Asesor jurídico"

        self.fields["anio"].widget = forms.Select(choices=self._anio_choices())
        self.fields["anio"].widget.attrs.setdefault("aria-label", "Año del protocolo")

        self.fields["fecha_inicio"].widget.attrs.setdefault("aria-label", "Fecha de inicio")
        self.fields["iniciales"].widget.attrs.setdefault("placeholder", "Ej. A.B.C.D.")
        self.fields["nombre_nna"].widget.attrs.setdefault(
            "placeholder", "Nombre completo del NNA"
        )

        sexo_field = self.fields["sexo"]
        sexo_choices = [
            (models.RelacionProtocolo.Sexo.HOMBRE, "Hombre"),
            (models.RelacionProtocolo.Sexo.MUJER, "Mujer"),
        ]
        if (
            self.instance
            and self.instance.sexo == models.RelacionProtocolo.Sexo.NO_ESPECIFICADO
            and models.RelacionProtocolo.Sexo.NO_ESPECIFICADO not in dict(sexo_choices)
        ):
            sexo_choices.append(
                (
                    models.RelacionProtocolo.Sexo.NO_ESPECIFICADO,
                    self.instance.get_sexo_display(),
                )
            )
        sexo_field.choices = sexo_choices
        if self.instance and self.instance.pk:
            sexo_field.initial = self.instance.sexo
        else:
            sexo_field.initial = models.RelacionProtocolo.Sexo.MUJER

        estatus_field = self.fields["estatus"]
        estatus_field.choices = models.RelacionProtocolo.Estatus.choices
        estatus_field.widget.attrs.setdefault("aria-label", "Estatus del caso")

        tipo_widget = self.fields["tipo_violencia"].widget
        tipo_widget.attrs.setdefault("list", "tipo-violencia-options")
        tipo_widget.attrs.setdefault(
            "placeholder",
            "Selecciona o escribe el tipo de violencia",
        )

        comentarios_widget = self.fields["comentarios"].widget
        comentarios_widget.attrs.setdefault("rows", 3)

        for name, field in self.fields.items():
            if isinstance(field.widget, forms.HiddenInput):
                continue
            TramiteForm._append_css_class(field.widget, "form-input")

        self.order_fields(
            [
                "numero_registro",
                "cct",
                "cct_codigo",
                "escuela",
                "anio",
                "fecha_inicio",
                "iniciales",
                "nombre_nna",
                "sexo",
                "asesor_juridico",
                "tipo_violencia",
                "descripcion",
                "comentarios",
                "estatus",
            ]
        )

    @staticmethod
    def _anio_choices() -> list[tuple[int, int]]:
        current_year = date.today().year
        return [(year, year) for year in range(current_year, current_year - 5, -1)]

    def clean_cct_codigo(self) -> str:
        codigo = self.cleaned_data.get("cct_codigo", "")
        if not codigo:
            raise forms.ValidationError("Debes proporcionar un CCT válido.")
        codigo = codigo.strip().upper()
        try:
            cct_obj = models.CCTSecundaria.objects.get(cct__iexact=codigo)
        except models.CCTSecundaria.DoesNotExist as exc:
            raise forms.ValidationError("No se encontró el CCT en el catálogo.") from exc
        self.cleaned_data["cct"] = cct_obj
        self.instance.cct = cct_obj
        self.cleaned_data["escuela"] = cct_obj.nombre
        self.cleaned_data["asesor_juridico"] = cct_obj.asesor
        return codigo

    def clean(self):
        cleaned = super().clean()
        fecha = cleaned.get("fecha_inicio")
        if fecha and not cleaned.get("anio"):
            cleaned["anio"] = fecha.year
            self.cleaned_data["anio"] = fecha.year
        cct = cleaned.get("cct")
        if cct:
            self.instance.cct = cct
            self.instance.escuela = cct.nombre
            self.instance.asesor_juridico = cct.asesor
            if not cleaned.get("escuela"):
                cleaned["escuela"] = cct.nombre
            if not cleaned.get("asesor_juridico"):
                cleaned["asesor_juridico"] = cct.asesor
        return cleaned


class ControlInternoForm(forms.ModelForm):
    cct_codigo = forms.CharField(
        label="CCT",
        help_text="Escribe la clave del centro de trabajo para autocompletar la información.",
    )

    class Meta:
        model = models.ControlInterno
        fields = (
            "memorandum",
            "fecha_memorandum",
            "anio",
            "numero_interno",
            "asunto",
            "cct",
            "cct_nombre",
            "sostenimiento_c_subcontrol",
            "tiponivelsub_c_servicion3",
            "fecha_contestacion",
            "numero_oficio_contestacion",
            "asesor",
            "observaciones",
            "estatus",
            "comentarios",
        )
        widgets = {
            "fecha_memorandum": forms.DateInput(attrs={"type": "date"}),
            "fecha_contestacion": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
            "comentarios": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ccts = models.CCTSecundaria.objects.order_by("cct")
        self.fields["cct"].queryset = ccts
        self.fields["cct"].required = False
        self.fields["cct"].widget = forms.HiddenInput()
        self.fields["cct_codigo"].widget.attrs.setdefault("list", "cct-options")
        self.fields["cct_codigo"].widget.attrs.setdefault(
            "placeholder", "Ej. 31EES0001H"
        )
        if self.instance and self.instance.cct_id:
            self.fields["cct_codigo"].initial = self.instance.cct_id
        self.fields["cct_nombre"].widget.attrs.setdefault(
            "placeholder", "Se llenará automáticamente al seleccionar el CCT."
        )
        sistema_field = self.fields["sostenimiento_c_subcontrol"]
        sistema_field.widget.attrs.setdefault(
            "placeholder", "Se llenará automáticamente al seleccionar el CCT."
        )
        self.fields["tiponivelsub_c_servicion3"].widget.attrs.setdefault(
            "placeholder", "Se llenará automáticamente al seleccionar el CCT."
        )
        self.fields["cct_nombre"].widget.attrs.setdefault("readonly", "readonly")
        sistema_field.widget.attrs.setdefault("readonly", "readonly")
        sistema_field.label = "Sistema"
        modalidad_field = self.fields["tiponivelsub_c_servicion3"]
        modalidad_field.widget.attrs.setdefault("readonly", "readonly")
        modalidad_field.label = "Modalidad"
        current_sistema = normalise_sistema(
            self.initial.get("sostenimiento_c_subcontrol")
            or getattr(self.instance, "sostenimiento_c_subcontrol", "")
        )
        self.initial["sostenimiento_c_subcontrol"] = current_sistema
        estatus_field = self.fields["estatus"]
        estatus_field.widget.attrs.setdefault("list", "estatus-options")
        estatus_field.widget.attrs.setdefault(
            "placeholder", "Selecciona o escribe el estatus."
        )
        if not self.instance.pk and "estatus" not in self.initial:
            estatus_field.initial = "NO ATENDIDO"
        self.fields["cct_nombre"].required = False
        sistema_field.required = False
        modalidad_field.required = False
        self.fields["anio"].widget.attrs.setdefault("list", "anio-options")
        self.fields["anio"].widget.attrs.setdefault(
            "placeholder", "Selecciona o escribe el año del memorándum."
        )
        self.fields["numero_oficio_contestacion"].widget.attrs.setdefault(
            "placeholder", "Ej. SE/SEB/DES-EESP/123/2025"
        )
        self.fields["numero_oficio_contestacion"].widget.attrs.setdefault(
            "list", "oficio-options"
        )
        for field in self.fields.values():
            TramiteForm._append_css_class(field.widget, "form-input")

    def clean_cct_codigo(self) -> str:
        codigo = self.cleaned_data.get("cct_codigo", "")
        if not codigo:
            raise forms.ValidationError("Debes proporcionar un CCT válido.")
        codigo = codigo.strip().upper()
        try:
            cct_obj = models.CCTSecundaria.objects.get(cct__iexact=codigo)
        except models.CCTSecundaria.DoesNotExist as exc:
            raise forms.ValidationError("No se encontró el CCT en el catálogo.") from exc
        self.cleaned_data["cct"] = cct_obj
        self.instance.cct = cct_obj
        self.cleaned_data["cct_nombre"] = cct_obj.nombre
        self.cleaned_data["sostenimiento_c_subcontrol"] = normalise_sistema(cct_obj.sostenimiento)
        self.cleaned_data["tiponivelsub_c_servicion3"] = cct_obj.servicio or ""
        if not self.cleaned_data.get("asesor"):
            self.cleaned_data["asesor"] = cct_obj.asesor
        return codigo

    def clean(self):
        cleaned = super().clean()
        cct_obj = cleaned.get("cct")
        if cct_obj:
            self.instance.cct_nombre = cct_obj.nombre
            self.instance.sostenimiento_c_subcontrol = normalise_sistema(cct_obj.sostenimiento)
            self.instance.tiponivelsub_c_servicion3 = cct_obj.servicio or ""
            if not cleaned.get("asesor"):
                cleaned["asesor"] = cct_obj.asesor
        cleaned["sostenimiento_c_subcontrol"] = normalise_sistema(
            cleaned.get("sostenimiento_c_subcontrol")
        )
        if not cleaned.get("estatus"):
            cleaned["estatus"] = "NO ATENDIDO"
        self.instance.estatus = cleaned["estatus"]
        return cleaned
