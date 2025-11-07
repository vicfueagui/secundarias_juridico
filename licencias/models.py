"""Modelos principales para la gestión de licencias."""
from __future__ import annotations

from datetime import date
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from licencias.services import validators
from licencias.utils import normalise_sistema


class CatalogoBase(models.Model):
    """Modelo base para catálogos simples."""

    nombre = models.CharField(max_length=255, unique=True)
    descripcion = models.TextField(blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True
        ordering = ("nombre",)

    def __str__(self) -> str:
        return self.nombre


class Subsistema(CatalogoBase):
    """Catálogo de subsistemas (Federal, Estatal, etc.)."""

    class Meta(CatalogoBase.Meta):
        verbose_name = "Subsistema"
        verbose_name_plural = "Subsistemas"


class TipoTramite(CatalogoBase):
    """Catálogo de tipos de trámite."""

    class Meta(CatalogoBase.Meta):
        verbose_name = "Tipo de Trámite"
        verbose_name_plural = "Tipos de Trámite"


class Etapa(CatalogoBase):
    """Catálogo de etapas del trámite."""

    orden = models.PositiveIntegerField(default=1)
    es_final = models.BooleanField(default=False)

    class Meta(CatalogoBase.Meta):
        ordering = ("orden", "nombre")
        verbose_name = "Etapa"
        verbose_name_plural = "Etapas"


class Sindicato(CatalogoBase):
    """Catálogo de sindicatos."""

    class Meta(CatalogoBase.Meta):
        verbose_name = "Sindicato"
        verbose_name_plural = "Sindicatos"


class Diagnostico(CatalogoBase):
    """Catálogo de diagnósticos."""

    class Meta(CatalogoBase.Meta):
        verbose_name = "Diagnóstico"
        verbose_name_plural = "Diagnósticos"


class Area(CatalogoBase):
    """Catálogo de áreas involucradas en los oficios."""

    class Meta(CatalogoBase.Meta):
        verbose_name = "Área"
        verbose_name_plural = "Áreas"


class Resultado(CatalogoBase):
    """Catálogo de resultados de resolución."""

    class Meta(CatalogoBase.Meta):
        verbose_name = "Resultado"
        verbose_name_plural = "Resultados"


class Tramite(models.Model):
    """Entidad central del sistema."""

    class TipoSolicitud(models.TextChoices):
        INICIAL = "inicial", _("Trámite inicial")
        PRIMERA_PRORROGA = "primera_prorroga", _("Primera prórroga")
        SEGUNDA_PRORROGA = "segunda_prorroga", _("Segunda prórroga")
        TERCERA_PRORROGA = "tercera_prorroga", _("Tercera prórroga")
        CUARTA_PRORROGA = "cuarta_prorroga", _("Cuarta prórroga")
        QUINTA_PRORROGA = "quinta_prorroga", _("Quinta prórroga")
        SEXTA_PRORROGA = "sexta_prorroga", _("Sexta prórroga")
        SEPTIMA_PRORROGA = "septima_prorroga", _("Séptima prórroga")
        OCTAVA_PRORROGA = "octava_prorroga", _("Octava prórroga")
        DESCONOCIDO = "otro", _("Otro / No especificado")

    FOLIO_PREFIX = "SEC-LIC"

    # Campos generales
    folio = models.CharField(max_length=25, unique=True, blank=True)
    estado_actual = models.ForeignKey(
        Etapa,
        on_delete=models.PROTECT,
        related_name="tramites",
        help_text="Etapa actual del trámite",
    )
    user_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tramites_asignados",
        blank=True,
        null=True,
    )
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ===== SECCIÓN 1: NIVEL EDUCATIVO =====
    tipo_tramite = models.ForeignKey(
        TipoTramite, on_delete=models.PROTECT, related_name="tramites",
        verbose_name="Licencia o trámite"
    )
    subsistema = models.ForeignKey(
        Subsistema, on_delete=models.PROTECT, related_name="tramites",
        verbose_name="Federal/Estatal"
    )
    tramite_inicial_o_prorroga = models.CharField(
        max_length=30,
        choices=TipoSolicitud.choices,
        default=TipoSolicitud.DESCONOCIDO,
        verbose_name="Trámite inicial o prórroga"
    )
    trabajador_nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre del trabajador"
    )
    diagnostico = models.ForeignKey(
        Diagnostico,
        on_delete=models.SET_NULL,
        related_name="tramites",
        blank=True,
        null=True,
        verbose_name="Diagnóstico"
    )
    sindicato = models.ForeignKey(
        Sindicato,
        on_delete=models.SET_NULL,
        related_name="tramites",
        blank=True,
        null=True,
        verbose_name="Nombre del sindicato"
    )
    contacto = models.TextField(
        blank=True,
        verbose_name="Contacto del trabajador y/o sindicato"
    )
    oficio_origen_num = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Número de oficio del sindicato o escrito de origen"
    )
    fecha_recepcion_nivel = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de recepción del oficio del sindicato o escrito del trabajador en el nivel educativo"
    )
    incidencias_integracion = models.TextField(
        blank=True,
        verbose_name="Incidencias para la integración del expediente/prevención/o contestación negativa del trámite"
    )
    oficio_envio_subsecretaria = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Oficio de envío a la Subsecretaría/PRÓRROGAS Oficio de envío a la Subd. de Org. y Adm. de Personal -DAF"
    )
    fecha_recepcion_subsecretaria = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de recepción en la Subsecretaría/PRÓRROGAS: Fecha de recepción en la Subd. de Org. y Adm. de Personal -DAF"
    )

    # ===== SECCIÓN 2: SEB/DEP. ASESORÍA TÉCNICA Y GESTIÓN DE LA INFORMACIÓN =====
    incidencias_vobo = models.TextField(
        blank=True,
        verbose_name="Incidencias para el visto bueno de la Subsecretaría"
    )
    vobo_num_y_fecha = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Número de oficio y fecha de Visto Bueno de la Subsecretaría"
    )
    fecha_recepcion_daf = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de recepción por la Subd. de Org. y Adm. de Personal -DAF"
    )

    # ===== SECCIÓN 3: APLICA PARA TRÁMITES ESTATALES/NIVEL EDUCATIVO y Prórrogas =====
    fecha_cita_valoracion = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de la cita de valoración del trabajador (TRÁMITES ESTATALES)"
    )
    fecha_contacto_cita = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de contacto al sindicato y al trabajador/señalar medio"
    )
    incidencias_contacto_cita = models.TextField(
        blank=True,
        verbose_name="Incidencias en el contacto para la cita de valoración"
    )

    # ===== SECCIÓN 4: NIVEL EDUCATIVO =====
    oficio_dictamen_num = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Número de oficio del Dictamen emitido por la Subd. de Org. y Adm. de Personal -DAF"
    )
    fecha_dictamen = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha del dictamen"
    )
    autorizado = models.BooleanField(
        default=False,
        verbose_name="Autorizado"
    )
    periodo_autorizado = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Periodo"
    )
    oficio_notificacion = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Oficio de Notificación realizada al sindicato y al trabajador"
    )
    fecha_notificacion = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha en la que se realizó la notificación al sindicato y al trabajador"
    )

    # ===== SECCIÓN 5: PRÓRROGAS/NIVEL EDUCATIVO =====
    # Primera prórroga
    prorroga1_oficio_origen = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prórroga 1: Número de oficio del sindicato o escrito de origen"
    )
    prorroga1_fecha_ingreso = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 1: Fecha de ingreso al nivel educativo"
    )
    prorroga1_incidencia = models.TextField(
        blank=True,
        verbose_name="Prórroga 1: Incidencia en la prórroga"
    )
    prorroga1_oficio_envio_daf = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prórroga 1: Número de oficio de envío a la Subd. de Org. y Adm. de Personal -DAF"
    )
    prorroga1_fecha_recepcion_daf = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 1: Fecha de recepción por la Subd. de Org. y Adm. de Personal -DAF"
    )
    prorroga1_fecha_cita = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 1: Fecha de la cita de valoración del trabajador (TRÁMITES ESTATALES)"
    )
    prorroga1_fecha_contacto = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 1: Fecha en la que se contactó al sindicato y al trabajador/señalar medio"
    )
    prorroga1_oficio_dictamen = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prórroga 1: Número de oficio del Dictamen emitido por la Subd. de Org. y Adm. de Personal -DAF"
    )
    prorroga1_fecha_dictamen = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 1: Fecha del dictamen"
    )
    prorroga1_autorizado = models.BooleanField(
        default=False,
        verbose_name="Prórroga 1: Autorizado"
    )
    prorroga1_periodo = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prórroga 1: Periodo"
    )
    prorroga1_oficio_notificacion = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prórroga 1: Oficio de Notificación de la prórroga realizada al sindicato y al trabajador"
    )
    prorroga1_fecha_notificacion = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 1: Fecha en la que se realizó la notificación al sindicato y al trabajador"
    )

    # Segunda prórroga
    prorroga2_oficio_origen = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prórroga 2: Número de oficio del sindicato o escrito de origen"
    )
    prorroga2_fecha_ingreso = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 2: Fecha de ingreso al nivel educativo"
    )
    prorroga2_incidencia = models.TextField(
        blank=True,
        verbose_name="Prórroga 2: Incidencia en la prórroga"
    )
    prorroga2_oficio_envio_daf = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prórroga 2: Número de oficio de envío a la Subd. de Org. y Adm. de Personal -DAF"
    )
    prorroga2_fecha_recepcion_daf = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 2: Fecha de recepción por la Subd. de Org. y Adm. de Personal -DAF"
    )
    prorroga2_fecha_cita = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 2: Fecha de la cita de valoración del trabajador (TRÁMITES ESTATALES)"
    )
    prorroga2_fecha_contacto = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 2: Fecha en la que se contactó al sindicato y al trabajador/señalar medio"
    )
    prorroga2_oficio_dictamen = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prórroga 2: Número de oficio del Dictamen emitido por la Subd. de Org. y Adm. de Personal -DAF"
    )
    prorroga2_fecha_dictamen = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 2: Fecha del dictamen"
    )
    prorroga2_autorizado = models.BooleanField(
        default=False,
        verbose_name="Prórroga 2: Autorizado"
    )
    prorroga2_periodo = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prórroga 2: Periodo"
    )
    prorroga2_oficio_notificacion = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prórroga 2: Oficio de Notificación de la prórroga realizada al sindicato y al trabajador"
    )
    prorroga2_fecha_notificacion = models.DateField(
        blank=True,
        null=True,
        verbose_name="Prórroga 2: Fecha en la que se realizó la notificación al sindicato y al trabajador"
    )

    # Campos legacy (mantener compatibilidad)
    oficio_envio_rh = models.CharField(max_length=100, blank=True)
    fecha_recepcion_rh = models.DateField(blank=True, null=True)
    oficio_resolucion_num_y_fecha = models.CharField(max_length=150, blank=True)
    resultado_resolucion = models.ForeignKey(
        Resultado,
        on_delete=models.SET_NULL,
        related_name="tramites",
        blank=True,
        null=True,
    )
    persona_tramita = models.CharField(max_length=255, blank=True)

    history = HistoricalRecords(inherit=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("folio",)),
            models.Index(fields=("trabajador_nombre",)),
            models.Index(fields=("estado_actual",)),
        ]

    def __str__(self) -> str:
        return f"{self.folio or 'SIN-FOLIO'} - {self.trabajador_nombre}"

    def clean(self) -> None:
        """Validaciones de negocio adicionales."""
        estado_anterior = None
        if self.pk:
            etapa_anterior_id = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("estado_actual", flat=True)
                .first()
            )
            if etapa_anterior_id:
                estado_anterior = Etapa.objects.filter(pk=etapa_anterior_id).first()
        validators.validar_fechas_chronologicas(self)
        validators.validar_campos_por_etapa(self)
        estado_actual = self.estado_actual if self.estado_actual_id else None
        validators.validar_transicion_etapa(estado_anterior, estado_actual)

    def save(self, *args, **kwargs) -> None:
        """Genera folio y ejecuta validaciones antes de guardar."""
        self.full_clean()
        if not self.folio:
            self.folio = self._generar_folio()
        super().save(*args, **kwargs)

    # --------------------------------------------------------------------- #
    # Reglas de negocio
    # --------------------------------------------------------------------- #
    def _generar_folio(self) -> str:
        """Genera un folio único bajo el patrón SEC-LIC-YYYY-####."""
        referencia = (
            self.fecha_recepcion_nivel
            or self.fecha_recepcion_subsecretaria
            or date.today()
        )
        anno = referencia.year
        prefijo = f"{self.FOLIO_PREFIX}-{anno}"
        ultimo_folio = (
            Tramite.objects.filter(folio__startswith=f"{prefijo}-")
            .order_by("-folio")
            .values_list("folio", flat=True)
            .first()
        )
        try:
            ultimo = int(ultimo_folio.split("-")[-1]) if ultimo_folio else 0
        except ValueError:
            ultimo = 0
        nuevo = ultimo + 1
        return f"{prefijo}-{nuevo:04d}"

    @property
    def etapa_anterior(self) -> Optional[Etapa]:
        """Devuelve la etapa anterior registrada, si existe."""
        movimiento = self.movimientos.order_by("-fecha").first()
        return movimiento.etapa_anterior if movimiento else None


class CCTSecundaria(models.Model):
    """Catálogo de centros de trabajo de nivel secundaria."""

    cct = models.CharField(
        max_length=12,
        primary_key=True,
        verbose_name="CCT",
        help_text="Clave de centro de trabajo",
    )
    nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre de la escuela",
    )
    asesor = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Asesor jurídico asignado",
    )
    servicio = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Modalidad",
        help_text="Modalidad registrada en el catálogo tiponivelsub_c_servicion3.",
    )
    sostenimiento = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Sistema",
        help_text="Sistema registrado en el catálogo de secundarias.",
    )
    municipio = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Municipio",
    )
    turno = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Turno",
    )
    history = HistoricalRecords()
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("cct",)
        verbose_name = "Centro de trabajo (Secundaria)"
        verbose_name_plural = "Centros de trabajo (Secundaria)"

    def __str__(self) -> str:
        return f"{self.cct} · {self.nombre}"


class ControlInterno(models.Model):
    """Registro del control de internos para el área jurídica."""

    memorandum = models.CharField(
        max_length=150,
        verbose_name="Memorándum",
        help_text="Identificador del memorándum asociado.",
    )
    fecha_memorandum = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha del memorándum",
    )
    anio = models.PositiveIntegerField(
        verbose_name="Año",
        validators=[
            MinValueValidator(2000),
            MaxValueValidator(date.today().year + 2),
        ],
    )
    numero_interno = models.CharField(
        max_length=100,
        verbose_name="Número interno",
    )
    asunto = models.CharField(
        max_length=255,
        verbose_name="Asunto",
    )
    cct = models.ForeignKey(
        CCTSecundaria,
        on_delete=models.PROTECT,
        related_name="controles_internos",
        verbose_name="CCT",
    )
    cct_nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre del centro de trabajo",
    )
    tiponivelsub_c_servicion3 = models.CharField(
        max_length=255,
        verbose_name="Modalidad",
        help_text="Modalidad educativa asociada al CCT.",
    )
    sostenimiento_c_subcontrol = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Sistema",
        help_text="Sistema del centro de trabajo.",
    )
    fecha_contestacion = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de contestación",
    )
    numero_oficio_contestacion = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Número de oficio de contestación",
    )
    asesor = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Asesor",
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )
    estatus = models.CharField(
        max_length=150,
        blank=True,
        default="NO ATENDIDO",
        verbose_name="Estatus",
    )
    comentarios = models.TextField(
        blank=True,
        verbose_name="Comentarios",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ("-fecha_memorandum", "-numero_interno")
        indexes = [
            models.Index(fields=("memorandum",)),
            models.Index(fields=("anio",)),
            models.Index(fields=("cct",)),
            models.Index(fields=("estatus",)),
        ]
        verbose_name = "Control de interno"
        verbose_name_plural = "Control de internos"

    def __str__(self) -> str:
        return f"{self.numero_interno} · {self.asunto}"

    def clean(self) -> None:
        if self.cct:
            self.cct_nombre = self.cct.nombre
            if not self.asesor:
                self.asesor = self.cct.asesor
            self.tiponivelsub_c_servicion3 = self.cct.servicio or ""
            self.sostenimiento_c_subcontrol = normalise_sistema(self.cct.sostenimiento)
        if self.anio:
            limite_superior = date.today().year + 2
            if self.anio < 2000 or self.anio > limite_superior:
                raise ValidationError(
                    {"anio": _("El año debe estar entre 2000 y %(limite)s.") % {"limite": limite_superior}}
                )
        if self.fecha_memorandum and not self.anio:
            self.anio = self.fecha_memorandum.year
        self.sostenimiento_c_subcontrol = normalise_sistema(self.sostenimiento_c_subcontrol)

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class ControlInternoStatusHistory(models.Model):
    """Registro cronológico de los cambios de estatus de un control interno."""

    control = models.ForeignKey(
        ControlInterno,
        on_delete=models.CASCADE,
        related_name="estatus_historial",
        verbose_name="Control interno",
    )
    estatus_anterior = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Estatus anterior",
    )
    estatus_nuevo = models.CharField(
        max_length=150,
        verbose_name="Estatus nuevo",
    )
    cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Registrado por",
    )
    cambiado_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de cambio")

    class Meta:
        ordering = ("-cambiado_en",)
        verbose_name = "Historial de estatus"
        verbose_name_plural = "Historial de estatus"

    def __str__(self) -> str:
        return f"{self.control} · {self.estatus_anterior or '—'} → {self.estatus_nuevo}"


class RelacionProtocolo(models.Model):
    """Registro de relación de protocolos para secundarias."""

    class Sexo(models.TextChoices):
        HOMBRE = "H", _("Hombre")
        MUJER = "M", _("Mujer")
        NO_ESPECIFICADO = "X", _("No especificado")

    class Estatus(models.TextChoices):
        ACTIVO = "activo", _("Activo")
        EN_SEGUIMIENTO = "seguimiento", _("En seguimiento")
        CERRADO = "cerrado", _("Cerrado")
        CANCELADO = "cancelado", _("Cancelado")

    numero_registro = models.PositiveIntegerField(
        unique=True,
        verbose_name="ID",
        help_text="Identificador correlativo utilizado en el control vigente",
    )
    cct = models.ForeignKey(
        CCTSecundaria,
        on_delete=models.PROTECT,
        related_name="protocolos",
        verbose_name="CCT",
    )
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    iniciales = models.CharField(
        max_length=50,
        verbose_name="Iniciales del NNA",
    )
    nombre_nna = models.CharField(
        max_length=255,
        verbose_name="Nombre del NNA",
    )
    sexo = models.CharField(
        max_length=1,
        choices=Sexo.choices,
        default=Sexo.MUJER,
        verbose_name="Sexo",
    )
    escuela = models.CharField(
        max_length=255,
        verbose_name="Escuela",
    )
    tipo_violencia = models.CharField(
        max_length=255,
        verbose_name="Tipo de violencia",
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción",
    )
    asesor_juridico = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nombre del asesor jurídico",
    )
    estatus = models.CharField(
        max_length=20,
        choices=Estatus.choices,
        default=Estatus.ACTIVO,
        verbose_name="Estatus",
    )
    comentarios = models.TextField(
        blank=True,
        verbose_name="Comentarios",
    )
    anio = models.PositiveIntegerField(
        verbose_name="Año",
        validators=[
            MinValueValidator(2000),
            MaxValueValidator(date.today().year + 1),
        ],
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ("-fecha_inicio", "-numero_registro")
        indexes = [
            models.Index(fields=("numero_registro",)),
            models.Index(fields=("anio",)),
            models.Index(fields=("estatus",)),
            models.Index(fields=("cct",)),
        ]
        verbose_name = "Relación de Protocolo"
        verbose_name_plural = "Relaciones de Protocolos"

    def __str__(self) -> str:
        return f"{self.numero_registro} · {self.nombre_nna}"

    def clean(self) -> None:
        if self.cct:
            self.escuela = self.cct.nombre
            if not self.asesor_juridico:
                self.asesor_juridico = self.cct.asesor
        if not self.anio and self.fecha_inicio:
            self.anio = self.fecha_inicio.year
        if self.anio:
            limite = date.today().year + 1
            if self.anio < 2000 or self.anio > limite:
                raise ValidationError(
                    {"anio": _("El año debe estar entre 2000 y %(limite)s.") % {"limite": limite}}
                )

    def save(self, *args, **kwargs) -> None:
        if not self.numero_registro:
            self.numero_registro = self.next_numero_registro()
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def next_numero_registro(cls) -> int:
        ultimo = (
            cls.objects.order_by("-numero_registro")
            .values_list("numero_registro", flat=True)
            .first()
            or 0
        )
        return ultimo + 1


class Oficio(models.Model):
    """Registro de oficios asociados al trámite."""

    class Tipo(models.TextChoices):
        ORIGEN = "origen", _("Oficio de origen")
        ENVIO_SUBSECRETARIA = "envio_subsecretaria", _("Envío a Subsecretaría")
        ENVIO_RH = "envio_rh", _("Envío a Recursos Humanos")
        VISTO_BUENO = "vobo", _("Visto Bueno")
        RESOLUCION = "resolucion", _("Resolución")
        NOTIFICACION_SINDICATO = "notif_sindicato", _("Notificación sindicato")
        NOTIFICACION_TRABAJADOR = "notif_trabajador", _("Notificación trabajador")
        OTRO = "otro", _("Otro")

    tramite = models.ForeignKey(
        Tramite, on_delete=models.CASCADE, related_name="oficios"
    )
    tipo = models.CharField(max_length=25, choices=Tipo.choices, default=Tipo.OTRO)
    numero = models.CharField(max_length=150, blank=True)
    fecha = models.DateField(blank=True, null=True)
    area_emisora = models.ForeignKey(
        Area, on_delete=models.SET_NULL, related_name="oficios", blank=True, null=True
    )
    observaciones = models.TextField(blank=True)
    history = HistoricalRecords()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-fecha", "tipo")
        verbose_name = "Oficio"
        verbose_name_plural = "Oficios"

    def __str__(self) -> str:
        return f"{self.tramite.folio} - {self.get_tipo_display()}"

    def clean(self) -> None:
        validators.validar_fecha_pasado(self.fecha, "fecha")


class Notificacion(models.Model):
    """Notificaciones emitidas a sindicato o trabajador."""

    class Destinatario(models.TextChoices):
        SINDICATO = "sindicato", _("Sindicato")
        TRABAJADOR = "trabajador", _("Trabajador")
        OTRO = "otro", _("Otro")

    tramite = models.ForeignKey(
        Tramite, on_delete=models.CASCADE, related_name="notificaciones"
    )
    destinatario = models.CharField(
        max_length=20, choices=Destinatario.choices, default=Destinatario.SINDICATO
    )
    numero_oficio = models.CharField(max_length=150, blank=True)
    fecha = models.DateField(blank=True, null=True)
    observaciones = models.TextField(blank=True)
    history = HistoricalRecords()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-fecha", "destinatario")
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self) -> str:
        return f"{self.tramite.folio} - {self.get_destinatario_display()}"

    def clean(self) -> None:
        validators.validar_fecha_pasado(self.fecha, "fecha")


class Movimiento(models.Model):
    """Historial de cambios de etapa."""

    tramite = models.ForeignKey(
        Tramite, on_delete=models.CASCADE, related_name="movimientos"
    )
    etapa_anterior = models.ForeignKey(
        Etapa,
        on_delete=models.SET_NULL,
        related_name="movimientos_salientes",
        blank=True,
        null=True,
    )
    etapa_nueva = models.ForeignKey(
        Etapa,
        on_delete=models.PROTECT,
        related_name="movimientos_entrantes",
    )
    comentario = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="movimientos_realizados",
        blank=True,
        null=True,
    )
    fecha = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    class Meta:
        ordering = ("-fecha",)
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"

    def __str__(self) -> str:
        return f"{self.tramite.folio} → {self.etapa_nueva.nombre}"

    def clean(self) -> None:
        if self.etapa_anterior and self.etapa_anterior == self.etapa_nueva:
            raise ValidationError("La etapa nueva debe ser distinta a la anterior.")
