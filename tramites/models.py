"""Modelos principales del módulo de trámites."""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from simple_history.models import HistoricalRecords

from tramites.incidencias import AFILIACION_CHOICES, apply_incidencias
from tramites.utils import normalise_sistema


class CatalogoBase(models.Model):
    """Modelo base para los catálogos del sistema."""

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


class CCTSecundaria(models.Model):
    """Catálogo de centros de trabajo de nivel secundaria."""

    cct = models.CharField(
        max_length=12,
        primary_key=True,
        verbose_name="CCT",
        help_text="Clave de centro de trabajo",
    )
    nombre = models.CharField(max_length=255, verbose_name="Nombre de la escuela")
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
    municipio = models.CharField(max_length=255, blank=True, verbose_name="Municipio")
    turno = models.CharField(max_length=255, blank=True, verbose_name="Turno")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("cct",)
        verbose_name = "Centro de trabajo (Secundaria)"
        verbose_name_plural = "Centros de trabajo (Secundaria)"

    def __str__(self) -> str:
        return f"{self.cct} · {self.nombre}"


class PlantillaCentroTrabajo(models.Model):
    """Centro de trabajo asociado a las plantillas de secundarias."""

    cct = models.CharField(max_length=12, primary_key=True, verbose_name="CCT")
    nombre = models.CharField(max_length=255, verbose_name="Nombre del centro de trabajo")
    municipio = models.CharField(max_length=255, blank=True, verbose_name="Municipio")
    asesor = models.CharField(max_length=255, blank=True, verbose_name="Asesor jurídico")
    sostenimiento = models.CharField(max_length=255, blank=True, verbose_name="Sostenimiento")
    subnivel = models.CharField(max_length=255, blank=True, verbose_name="Subnivel")
    turno = models.CharField(max_length=255, blank=True, verbose_name="Turno")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("cct",)
        verbose_name = "Centro de trabajo (Plantilla secundaria)"
        verbose_name_plural = "Centros de trabajo (Plantilla secundaria)"

    def __str__(self) -> str:
        return f"{self.cct} · {self.nombre}"


class PlantillaEmpleado(models.Model):
    """Empleado asociado a las plantillas de secundarias."""

    nombre = models.CharField(max_length=255, verbose_name="Nombre del empleado")
    rfc = models.CharField(max_length=13, blank=True, null=True, db_index=True, unique=True)
    curp = models.CharField(max_length=18, blank=True, null=True, db_index=True, unique=True)
    correo = models.EmailField(blank=True, verbose_name="Correo")
    telefono = models.CharField(max_length=255, blank=True, verbose_name="Teléfono")
    celular = models.CharField(max_length=50, blank=True, verbose_name="Celular")
    direccion = models.CharField(max_length=255, blank=True, verbose_name="Dirección")
    colonia = models.CharField(max_length=255, blank=True, verbose_name="Colonia")
    codigo_postal = models.CharField(max_length=10, blank=True, verbose_name="Código postal")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre",)
        verbose_name = "Empleado (Plantilla secundaria)"
        verbose_name_plural = "Empleados (Plantilla secundaria)"

    def __str__(self) -> str:
        return f"{self.nombre} · {self.rfc or self.curp or 'Sin RFC/Curp'}"


class PlantillaRegistro(models.Model):
    """Registro histórico de plantillas por ciclo escolar."""

    origen_id = models.PositiveIntegerField(
        unique=True,
        blank=True,
        null=True,
        verbose_name="ID de origen",
    )
    centro_trabajo = models.ForeignKey(
        PlantillaCentroTrabajo,
        on_delete=models.PROTECT,
        related_name="registros",
    )
    empleado = models.ForeignKey(
        PlantillaEmpleado,
        on_delete=models.PROTECT,
        related_name="registros",
    )
    situacion = models.CharField(max_length=255, blank=True, verbose_name="Situación")
    funcion = models.CharField(max_length=255, blank=True, verbose_name="Función")
    grado_grupo_horas = models.CharField(max_length=255, blank=True, verbose_name="Grado/Grupo/Horas")
    ciclo = models.CharField(max_length=20, blank=True, verbose_name="Ciclo escolar")
    anio = models.PositiveSmallIntegerField(blank=True, null=True, db_index=True, verbose_name="Año")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-anio", "-ciclo", "empleado")
        verbose_name = "Registro de plantilla (Secundaria)"
        verbose_name_plural = "Registros de plantilla (Secundaria)"
        indexes = [
            models.Index(fields=("ciclo",)),
            models.Index(fields=("empleado", "anio")),
            models.Index(
                fields=("empleado", "anio", "ciclo"),
                name="pl_reg_emp_anio_ciclo_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.empleado} · {self.centro_trabajo} · {self.ciclo or self.anio}"


class PlantillaClavePresupuestal(models.Model):
    """Clave presupuestal asociada a un registro de plantilla."""

    registro = models.ForeignKey(
        PlantillaRegistro,
        on_delete=models.CASCADE,
        related_name="claves",
    )
    clave = models.CharField(max_length=128, verbose_name="Clave presupuestal")

    class Meta:
        verbose_name = "Clave presupuestal (Plantilla)"
        verbose_name_plural = "Claves presupuestales (Plantilla)"
        unique_together = ("registro", "clave")

    def __str__(self) -> str:
        return self.clave


class TipoProceso(CatalogoBase):
    """Catálogo de tipos de trámite utilizados en el registro."""

    es_documento = models.BooleanField(
        default=False,
        help_text="Indica si requiere documentos adicionales.",
    )

    class Meta(CatalogoBase.Meta):
        verbose_name = "Tipo de trámite"
        verbose_name_plural = "Tipos de trámite"


class PlantillaCapturaTipo(models.Model):
    """Plantilla de captura guiada por tipo de trámite y ámbito."""

    AMBITO_CASO = "caso"
    AMBITO_TRAMITE = "tramite"
    AMBITO_CHOICES = (
        (AMBITO_CASO, "Trámite principal"),
        (AMBITO_TRAMITE, "Trámite asociado"),
    )

    tipo_proceso = models.ForeignKey(
        TipoProceso,
        on_delete=models.CASCADE,
        related_name="plantillas_captura",
        verbose_name="Tipo de trámite",
    )
    ambito = models.CharField(
        max_length=20,
        choices=AMBITO_CHOICES,
        default=AMBITO_CASO,
        db_index=True,
        verbose_name="Ámbito",
    )
    nombre = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Nombre de plantilla",
        help_text="Etiqueta opcional para identificar la configuración en operación.",
    )
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    reglas_campos = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Reglas de campos",
        help_text=(
            "Define campos visibles/requeridos por estatus. "
            "Formato esperado: managed_fields, default_visible_fields, "
            "default_required_fields y status_rules."
        ),
    )
    checklist_etapas = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Checklist documental por etapas",
        help_text=(
            "Lista de etapas con documentos. Cada documento puede marcarse "
            "como crítico para bloquear avance."
        ),
    )
    esta_activa = models.BooleanField(default=True, db_index=True)
    orden = models.PositiveSmallIntegerField(default=1)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tipo_proceso__nombre", "ambito", "orden", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("tipo_proceso", "ambito"),
                name="plantilla_captura_tipo_ambito_unica",
            )
        ]
        indexes = [
            models.Index(fields=("ambito", "esta_activa")),
        ]
        verbose_name = "Plantilla de captura guiada"
        verbose_name_plural = "Plantillas de captura guiada"

    def __str__(self) -> str:
        etiqueta = self.nombre.strip() if self.nombre else self.tipo_proceso.nombre
        return f"{etiqueta} · {self.get_ambito_display()}"


class AreaProceso(CatalogoBase):
    """Catálogo de áreas o dependencias involucradas en los trámites."""

    siglas = models.CharField(max_length=50, blank=True)

    class Meta(CatalogoBase.Meta):
        verbose_name = "Área de proceso"
        verbose_name_plural = "Áreas de proceso"


class EstatusCaso(CatalogoBase):
    """Catálogo de estatus aplicables a cada trámite."""

    orden = models.PositiveIntegerField(default=1)

    class Meta(CatalogoBase.Meta):
        ordering = ("orden", "nombre")
        verbose_name = "Estatus de caso"
        verbose_name_plural = "Estatus de caso"


class TipoViolencia(CatalogoBase):
    """Catálogo de tipos de violencia (opcional en el trámite)."""

    class Meta(CatalogoBase.Meta):
        verbose_name = "Tipo de violencia"
        verbose_name_plural = "Tipos de violencia"


class PrefijoOficio(CatalogoBase):
    """Catálogo de prefijos sugeridos para el número de oficio."""

    class Meta(CatalogoBase.Meta):
        verbose_name = "Prefijo de oficio"
        verbose_name_plural = "Prefijos de oficio"


class Solicitante(CatalogoBase):
    """Catálogo de solicitantes de trámites."""

    class Meta(CatalogoBase.Meta):
        verbose_name = "Solicitante"
        verbose_name_plural = "Solicitantes"

    def __str__(self) -> str:
        return f"{self.nombre} · {self.descripcion}" if self.descripcion else self.nombre


class Destinatario(CatalogoBase):
    """Catálogo de destinatarios (dirigido a)."""

    class Meta(CatalogoBase.Meta):
        verbose_name = "Destinatario"
        verbose_name_plural = "Destinatarios"

    def __str__(self) -> str:
        return f"{self.nombre} · {self.descripcion}" if self.descripcion else self.nombre


class EstatusTramite(CatalogoBase):
    """Catálogo de estatus específicos para trámites del caso."""

    orden = models.PositiveIntegerField(default=1)

    class Meta(CatalogoBase.Meta):
        ordering = ("orden", "nombre")
        verbose_name = "Estatus de trámite"
        verbose_name_plural = "Estatus de trámite"


SEXO_NNA_CHOICES = (
    ("M", "Mujer"),
    ("H", "Hombre"),
)

TIPO_LICENCIA_CHOICES = (
    ("licencia_754", "Licencia 754"),
    ("cambio_funcion", "Cambio de función"),
    ("licencia_70_bis", "Licencia 70 BIS"),
    ("cambio_actividad", "Cambio de actividad"),
)

TIPO_PRORROGA_CHOICES = (
    ("inicial", "Inicial"),
    ("primera_prorroga", "Primera prórroga"),
    ("segunda_prorroga", "Segunda prórroga"),
    ("tercera_prorroga", "Tercera prórroga"),
    ("cuarta_prorroga", "Cuarta prórroga"),
    ("quinta_prorroga", "Quinta prórroga"),
)

SINDICATO_CHOICES = (
    ("sytte", "SYTTE"),
    ("snte_33", "SNTE sección 33"),
    ("snte_57", "SNTE sección 57"),
    ("setey", "SETEY"),
    ("gnte", "GNTE"),
    ("sitem", "SITEM"),
)

RESPUESTA_OFICIO_CHOICES = (
    (
        "subsecretaria_basica_prorrogas",
        "Oficio de envío a la Subsecretaría Básica / Prórrogas",
    ),
    (
        "subd_org_personal_daf",
        "Oficio de envío a la Subd. de Org. y Adm. de Personal - DAF",
    ),
    (
        "incidencias_integracion",
        "Incidencias para la integración del expediente",
    ),
    ("prevencion", "Prevención del trámite"),
    ("contestacion_negativa", "Contestación negativa del trámite"),
)

VISTO_BUENO_CHOICES = (
    (
        "visto_bueno_subsecretaria_basica",
        "Visto bueno por la Subsecretaría Básica",
    ),
    (
        "incidencias_visto_bueno",
        "Incidencias para el visto bueno de la Subsecretaría",
    ),
)

CITA_VALORACION_CHOICES = (
    ("cita_valoracion", "Cita de valoración del trabajador"),
    ("incidencias_contacto", "Incidencias en el contacto para la cita de valoración"),
)


class CasoInterno(models.Model):
    """Trámite registrado para cada centro de trabajo."""

    cct = models.ForeignKey(
        PlantillaCentroTrabajo,
        on_delete=models.PROTECT,
        related_name="casos",
        verbose_name="CCT principal",
    )
    cct_nombre = models.CharField(max_length=255, verbose_name="Nombre del CCT")
    cct_sistema = models.CharField(max_length=255, blank=True, verbose_name="Sistema")
    cct_modalidad = models.CharField(max_length=255, blank=True, verbose_name="Modalidad")
    asesor_cct = models.CharField(max_length=255, blank=True, verbose_name="Asesor asignado")
    descripcion_breve = models.CharField(max_length=255, blank=True, verbose_name="Descripción breve")
    fecha_apertura = models.DateField(verbose_name="Fecha de apertura")
    estatus = models.ForeignKey(
        EstatusCaso,
        on_delete=models.PROTECT,
        related_name="casos",
        verbose_name="Estatus",
    )
    tipo_inicial = models.ForeignKey(
        TipoProceso,
        on_delete=models.PROTECT,
        related_name="casos_iniciados_como",
        verbose_name="Tipo inicial",
    )
    tipo_violencia = models.ForeignKey(
        TipoViolencia,
        on_delete=models.SET_NULL,
        related_name="casos",
        verbose_name="Tipo de violencia",
        blank=True,
        null=True,
    )
    tipos_violencia_adicionales = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Tipos de violencia adicionales",
    )
    numero_oficio = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Número de expediente",
    )
    tipo_prorroga = models.CharField(
        max_length=30,
        choices=TIPO_PRORROGA_CHOICES,
        blank=True,
        default="",
        verbose_name="Trámite inicial o prórroga",
    )
    sindicato = models.CharField(
        max_length=30,
        choices=SINDICATO_CHOICES,
        blank=True,
        default="",
        verbose_name="Nombre del sindicato",
    )
    diagnostico = models.TextField(blank=True, default="", verbose_name="Diagnóstico")
    solicitante = models.ForeignKey(
        Solicitante,
        on_delete=models.SET_NULL,
        related_name="casos",
        verbose_name="Solicitante",
        blank=True,
        null=True,
    )
    dirigido_a = models.ForeignKey(
        Destinatario,
        on_delete=models.SET_NULL,
        related_name="casos",
        verbose_name="Dirigido a",
        blank=True,
        null=True,
    )
    generador_nombre = models.CharField(max_length=255, blank=True, verbose_name="Nombre del generador")
    generador_iniciales = models.CharField(max_length=50, blank=True, verbose_name="Iniciales del NNA (generador)")
    generador_sexo = models.CharField(
        max_length=1, blank=True, choices=SEXO_NNA_CHOICES, verbose_name="Sexo del NNA (generador)"
    )
    receptor_nombre = models.CharField(max_length=255, blank=True, verbose_name="Nombre del receptor")
    receptor_iniciales = models.CharField(max_length=50, blank=True, verbose_name="Iniciales del NNA (receptor)")
    receptor_sexo = models.CharField(
        max_length=1, blank=True, choices=SEXO_NNA_CHOICES, verbose_name="Sexo del NNA (receptor)"
    )
    receptores_adicionales = models.JSONField(default=list, blank=True, verbose_name="Receptores adicionales")
    generadores_adicionales = models.JSONField(
        default=list, blank=True, verbose_name="Generadores adicionales"
    )
    asunto = models.TextField(blank=True, verbose_name="Asunto")
    folio_inicial = models.CharField(max_length=150, blank=True, verbose_name="Folio inicial")
    area_origen_inicial = models.ForeignKey(
        AreaProceso,
        on_delete=models.PROTECT,
        related_name="casos_origen",
        verbose_name="Área de origen",
        blank=True,
        null=True,
    )
    fecha_oficio_inicial = models.DateField(blank=True, null=True, verbose_name="Fecha oficio inicial")
    asunto_inicial = models.CharField(max_length=255, blank=True, verbose_name="Asunto inicial")
    observaciones_iniciales = models.TextField(blank=True, verbose_name="Observaciones iniciales")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="casos_creados",
        verbose_name="Registrado por",
        blank=True,
        null=True,
    )
    usuarios_involucrados = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="casos_involucrados",
        blank=True,
        verbose_name="Usuarios involucrados",
    )
    trabajadores = models.ManyToManyField(
        PlantillaEmpleado,
        through="CasoTrabajador",
        related_name="casos_tramites",
        blank=True,
        verbose_name="Trabajadores vinculados",
    )
    trabajadores_manuales = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Trabajadores manuales del caso",
        help_text="Trabajadores capturados localmente para este caso sin afectar la plantilla.",
    )
    centros_trabajo_adicionales = models.ManyToManyField(
        PlantillaCentroTrabajo,
        related_name="casos_adicionales",
        blank=True,
        verbose_name="Centros de trabajo adicionales",
    )
    fecha_termino = models.DateField(blank=True, null=True, verbose_name="Fecha de término")
    incidencia_nombre_docente = models.CharField(max_length=255, blank=True, verbose_name="Nombre del docente")
    incidencia_afiliacion = models.CharField(
        max_length=10,
        blank=True,
        choices=AFILIACION_CHOICES,
        verbose_name="Afiliación (IMSS/ISSSTE)",
    )
    incidencia_fecha_inicio = models.DateField(blank=True, null=True, verbose_name="Fecha de inicio de incidencia")
    incidencia_fecha_termino = models.DateField(blank=True, null=True, verbose_name="Fecha término de incidencia")
    incidencia_dias_otorgados = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Días otorgados (naturales)",
    )
    rangos_fechas_adicionales = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Rangos de fechas adicionales",
    )
    minuta = models.FileField(
        upload_to="tramites/minutas/casos/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["pdf"])],
        verbose_name="Documento (PDF)",
    )
    checklist_documental = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Checklist documental",
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ("-fecha_apertura", "-fecha_registro")
        indexes = [
            models.Index(fields=("cct",)),
            models.Index(fields=("estatus",)),
            models.Index(fields=("fecha_apertura",)),
        ]
        verbose_name = "Trámite"
        verbose_name_plural = "Trámites"

    def __str__(self) -> str:
        return f"{self.cct} · {self.descripcion_breve}"

    def clean(self) -> None:
        super().clean()
        if self.cct:
            self.cct_nombre = self.cct.nombre
            self.cct_sistema = normalise_sistema(self.cct.sostenimiento)
            self.cct_modalidad = self.cct.subnivel or ""
            if not self.asesor_cct:
                self.asesor_cct = self.cct.asesor
        self.cct_sistema = normalise_sistema(self.cct_sistema)
        apply_incidencias(self, error_class=ValidationError)

    @property
    def dias_para_termino(self) -> int | None:
        """Devuelve días restantes para la fecha de término, si existe."""
        if not self.fecha_termino:
            return None
        today = timezone.localdate()
        return (self.fecha_termino - today).days

    @property
    def dias_para_termino_abs(self) -> int | None:
        """Devuelve el valor absoluto de los días restantes."""
        dias = self.dias_para_termino
        if dias is None:
            return None
        return abs(dias)


class CasoTrabajador(models.Model):
    """Relación entre casos y trabajadores (plantilla)."""

    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.CASCADE,
        related_name="trabajadores_caso",
    )
    trabajador = models.ForeignKey(
        PlantillaEmpleado,
        on_delete=models.PROTECT,
        related_name="casos_trabajador",
    )
    es_principal = models.BooleanField(default=False, verbose_name="Trabajador principal")
    centro_trabajo_preferido = models.ForeignKey(
        PlantillaCentroTrabajo,
        on_delete=models.SET_NULL,
        related_name="trabajadores_preferidos",
        blank=True,
        null=True,
        verbose_name="Centro de trabajo preferido",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-creado_en",)
        constraints = [
            models.UniqueConstraint(
                fields=("caso",),
                condition=Q(es_principal=True),
                name="caso_un_trabajador_principal",
            ),
            models.UniqueConstraint(
                fields=("caso", "trabajador"),
                name="caso_trabajador_unico",
            ),
        ]
        verbose_name = "Trabajador del caso"
        verbose_name_plural = "Trabajadores del caso"

    def __str__(self) -> str:
        return f"{self.trabajador} · Caso #{self.caso_id}"


class HistorialEstatusCaso(models.Model):
    """Bitácora de cambios de estatus en los trámites."""

    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.CASCADE,
        related_name="historial_estatus",
        verbose_name="Caso",
    )
    estatus_anterior = models.ForeignKey(
        EstatusCaso,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        verbose_name="Estatus anterior",
    )
    estatus_nuevo = models.ForeignKey(
        EstatusCaso,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="Estatus nuevo",
    )
    fecha_estatus = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha del estatus",
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de cambio")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="cambios_estatus_casos",
        blank=True,
        null=True,
        verbose_name="Registrado por",
    )
    comentario = models.TextField(blank=True, verbose_name="Comentario")

    class Meta:
        ordering = ("-fecha_cambio",)
        verbose_name = "Historial de estatus de trámite"
        verbose_name_plural = "Historial de estatus de trámites"

    def __str__(self) -> str:
        return f"{self.caso} · {self.estatus_anterior or '—'} → {self.estatus_nuevo}"

    @property
    def fecha_estatus_resuelta(self):
        if self.fecha_estatus:
            return self.fecha_estatus
        if not self.fecha_cambio:
            return None
        if timezone.is_aware(self.fecha_cambio):
            return timezone.localtime(self.fecha_cambio).date()
        return self.fecha_cambio.date()


class HistorialEstatusTramiteCaso(models.Model):
    """Bitácora de cambios de estatus para los trámites asociados a un caso."""

    tramite = models.ForeignKey(
        "TramiteCaso",
        on_delete=models.CASCADE,
        related_name="historial_estatus",
        verbose_name="Trámite del caso",
    )
    estatus_anterior = models.ForeignKey(
        EstatusTramite,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        verbose_name="Estatus anterior",
    )
    estatus_nuevo = models.ForeignKey(
        EstatusTramite,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="Estatus nuevo",
    )
    fecha_estatus = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha del estatus",
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de cambio")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="cambios_estatus_tramites",
        blank=True,
        null=True,
        verbose_name="Registrado por",
    )
    comentario = models.TextField(blank=True, verbose_name="Comentario")

    class Meta:
        ordering = ("-fecha_cambio",)
        verbose_name = "Historial de estatus de trámite asociado"
        verbose_name_plural = "Historial de estatus de trámites asociados"

    def __str__(self) -> str:
        return f"{self.tramite} · {self.estatus_anterior or '—'} → {self.estatus_nuevo}"

    @property
    def fecha_estatus_resuelta(self):
        if self.fecha_estatus:
            return self.fecha_estatus
        if not self.fecha_cambio:
            return None
        if timezone.is_aware(self.fecha_cambio):
            return timezone.localtime(self.fecha_cambio).date()
        return self.fecha_cambio.date()


class BitacoraCaso(models.Model):
    """Bitácora de acciones relevantes sobre casos."""

    ACCION_CHOICES = (
        ("convertir_anexo", "Convertir a trámite anexo"),
        ("unir_casos", "Unir casos"),
    )

    accion = models.CharField(max_length=50, choices=ACCION_CHOICES)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="bitacoras_casos",
    )
    caso_origen = models.ForeignKey(
        CasoInterno,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="bitacoras_origen",
    )
    caso_destino = models.ForeignKey(
        CasoInterno,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="bitacoras_destino",
    )
    tramite = models.ForeignKey(
        "TramiteCaso",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="bitacoras",
    )
    detalle = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-creado_en",)
        verbose_name = "Bitácora de caso"
        verbose_name_plural = "Bitácoras de caso"

    def __str__(self) -> str:
        return f"{self.get_accion_display()} · {self.caso_origen_id} → {self.caso_destino_id}"


class CasoComentarioInterno(models.Model):
    """Comentarios internos ligados al expediente/caso."""

    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.CASCADE,
        related_name="comentarios_internos",
        verbose_name="Caso",
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="comentarios_caso",
        blank=True,
        null=True,
        verbose_name="Autor",
    )
    mensaje = models.TextField(verbose_name="Comentario")
    menciones = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="comentarios_mencionados",
        blank=True,
        verbose_name="Usuarios mencionados",
    )
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-creado_en", "-id")
        indexes = [
            models.Index(fields=("caso", "creado_en")),
        ]
        verbose_name = "Comentario interno de caso"
        verbose_name_plural = "Comentarios internos de caso"

    def __str__(self) -> str:
        return f"Caso #{self.caso_id} · {self.autor or 'Sin autor'} · {self.creado_en:%Y-%m-%d %H:%M}"


class CasoTareaInterna(models.Model):
    """Tareas/acuerdos internos asociados al expediente/caso."""

    ESTADO_PENDIENTE = "pendiente"
    ESTADO_COMPLETADA = "completada"
    ESTADO_CHOICES = (
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_COMPLETADA, "Completada"),
    )

    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.CASCADE,
        related_name="tareas_internas",
        verbose_name="Caso",
    )
    titulo = models.CharField(max_length=220, verbose_name="Tarea / acuerdo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tareas_internas_responsable",
        verbose_name="Responsable",
    )
    fecha_compromiso = models.DateField(db_index=True, verbose_name="Fecha compromiso")
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE,
        db_index=True,
    )
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tareas_internas_creadas",
        blank=True,
        null=True,
        verbose_name="Creada por",
    )
    completada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tareas_internas_completadas",
        blank=True,
        null=True,
        verbose_name="Completada por",
    )
    completada_en = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de completado")
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("fecha_compromiso", "-creado_en")
        indexes = [
            models.Index(fields=("caso", "estado", "fecha_compromiso")),
            models.Index(fields=("responsable", "estado")),
        ]
        verbose_name = "Tarea interna de caso"
        verbose_name_plural = "Tareas internas de caso"

    def __str__(self) -> str:
        return f"Caso #{self.caso_id} · {self.titulo}"

    @property
    def esta_vencida(self) -> bool:
        if self.estado == self.ESTADO_COMPLETADA:
            return False
        return self.fecha_compromiso < timezone.localdate()

    @property
    def dias_restantes(self) -> int:
        return (self.fecha_compromiso - timezone.localdate()).days

    @property
    def dias_restantes_abs(self) -> int:
        return abs(self.dias_restantes)

    def marcar_completada(self, *, usuario=None) -> bool:
        if self.estado == self.ESTADO_COMPLETADA:
            return False
        actor = usuario if getattr(usuario, "is_authenticated", False) else None
        self.estado = self.ESTADO_COMPLETADA
        self.completada_en = timezone.now()
        self.completada_por = actor
        self.save(update_fields=["estado", "completada_en", "completada_por", "actualizado_en"])
        return True


class TramiteCaso(models.Model):
    """Trámites adicionales asociados a un caso para seguimiento."""

    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.CASCADE,
        related_name="tramites_relacionados",
        verbose_name="Caso",
    )
    cct = models.ForeignKey(
        PlantillaCentroTrabajo,
        on_delete=models.PROTECT,
        related_name="tramites_asociados",
        verbose_name="CCT del trámite",
        blank=True,
        null=True,
    )
    cct_nombre = models.CharField(max_length=255, blank=True, verbose_name="Nombre del CCT")
    cct_sistema = models.CharField(max_length=255, blank=True, verbose_name="Sistema")
    cct_modalidad = models.CharField(max_length=255, blank=True, verbose_name="Modalidad")
    asesor_cct = models.CharField(max_length=255, blank=True, verbose_name="Asesor asignado")
    tipo = models.ForeignKey(
        TipoProceso,
        on_delete=models.PROTECT,
        related_name="tramites_caso",
        verbose_name="Tipo de trámite",
    )
    estatus = models.ForeignKey(
        EstatusTramite,
        on_delete=models.PROTECT,
        related_name="tramites_caso",
        verbose_name="Estatus del trámite",
        blank=True,
        null=True,
    )
    tipo_violencia = models.ForeignKey(
        TipoViolencia,
        on_delete=models.SET_NULL,
        related_name="tramites_caso",
        verbose_name="Tipo de violencia",
        blank=True,
        null=True,
    )
    tipos_violencia_adicionales = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Tipos de violencia adicionales",
    )
    solicitante = models.ForeignKey(
        Solicitante,
        on_delete=models.SET_NULL,
        related_name="tramites_caso",
        verbose_name="Solicitante",
        blank=True,
        null=True,
    )
    dirigido_a = models.ForeignKey(
        Destinatario,
        on_delete=models.SET_NULL,
        related_name="tramites_caso",
        verbose_name="Dirigido a",
        blank=True,
        null=True,
    )
    fecha = models.DateField(verbose_name="Fecha del trámite")
    numero_oficio = models.CharField(max_length=150, blank=True, verbose_name="Número de expediente")
    tipo_prorroga = models.CharField(
        max_length=30,
        choices=TIPO_PRORROGA_CHOICES,
        blank=True,
        default="",
        verbose_name="Trámite inicial o prórroga",
    )
    sindicato = models.CharField(
        max_length=30,
        choices=SINDICATO_CHOICES,
        blank=True,
        default="",
        verbose_name="Nombre del sindicato",
    )
    diagnostico = models.TextField(blank=True, default="", verbose_name="Diagnóstico")
    asunto = models.CharField(max_length=255, blank=True, verbose_name="Asunto")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    generador_nombre = models.CharField(max_length=255, blank=True, verbose_name="Nombre del generador")
    generador_iniciales = models.CharField(max_length=50, blank=True, verbose_name="Iniciales del NNA (generador)")
    generador_sexo = models.CharField(
        max_length=1, blank=True, choices=SEXO_NNA_CHOICES, verbose_name="Sexo del NNA (generador)"
    )
    receptor_nombre = models.CharField(max_length=255, blank=True, verbose_name="Nombre del receptor")
    receptor_iniciales = models.CharField(max_length=50, blank=True, verbose_name="Iniciales del NNA (receptor)")
    receptor_sexo = models.CharField(
        max_length=1, blank=True, choices=SEXO_NNA_CHOICES, verbose_name="Sexo del NNA (receptor)"
    )
    receptores_adicionales = models.JSONField(default=list, blank=True, verbose_name="Receptores adicionales")
    generadores_adicionales = models.JSONField(
        default=list, blank=True, verbose_name="Generadores adicionales"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    fecha_termino = models.DateField(blank=True, null=True, verbose_name="Fecha de término")
    incidencia_nombre_docente = models.CharField(max_length=255, blank=True, verbose_name="Nombre del docente")
    incidencia_afiliacion = models.CharField(
        max_length=10,
        blank=True,
        choices=AFILIACION_CHOICES,
        verbose_name="Afiliación (IMSS/ISSSTE)",
    )
    incidencia_fecha_inicio = models.DateField(blank=True, null=True, verbose_name="Fecha de inicio de incidencia")
    incidencia_fecha_termino = models.DateField(blank=True, null=True, verbose_name="Fecha término de incidencia")
    incidencia_dias_otorgados = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Días otorgados (naturales)",
    )
    rangos_fechas_adicionales = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Rangos de fechas adicionales",
    )
    minuta = models.FileField(
        upload_to="tramites/minutas/tramites/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["pdf"])],
        verbose_name="Documento (PDF)",
    )
    checklist_documental = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Checklist documental",
    )
    usuarios_involucrados = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="tramites_involucrados",
        blank=True,
        verbose_name="Usuarios involucrados",
    )
    es_iniciador = models.BooleanField(
        default=False,
        verbose_name="Trámite iniciador del caso",
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ("-fecha", "-creado_en")
        verbose_name = "Trámite del caso"
        verbose_name_plural = "Trámites del caso"
        constraints = [
            models.UniqueConstraint(
                fields=("caso",),
                condition=Q(es_iniciador=True),
                name="tramites_un_iniciador_por_caso",
            )
        ]

    def __str__(self) -> str:
        return f"{self.caso} · {self.tipo} · {self.fecha}"

    @property
    def dias_para_termino(self) -> int | None:
        if not self.fecha_termino:
            return None
        today = timezone.localdate()
        return (self.fecha_termino - today).days

    @property
    def dias_para_termino_abs(self) -> int | None:
        dias = self.dias_para_termino
        if dias is None:
            return None
        return abs(dias)

    def clean(self) -> None:
        super().clean()
        if self.cct:
            self.cct_nombre = self.cct.nombre
            self.cct_sistema = normalise_sistema(self.cct.sostenimiento)
            self.cct_modalidad = self.cct.subnivel or ""
            if not self.asesor_cct:
                self.asesor_cct = self.cct.asesor
        elif self.caso_id and self.caso:
            if not self.cct_nombre:
                self.cct_nombre = self.caso.cct_nombre
            if not self.cct_sistema:
                self.cct_sistema = self.caso.cct_sistema
            if not self.cct_modalidad:
                self.cct_modalidad = self.caso.cct_modalidad
            if not self.asesor_cct:
                self.asesor_cct = self.caso.asesor_cct
        self.cct_sistema = normalise_sistema(self.cct_sistema)
        apply_incidencias(self, error_class=ValidationError)


class BandejaNotificacion(models.Model):
    """Notificación interna para la bandeja de entrada."""

    EVENTO_CHOICES = (
        ("caso_creado", "Caso creado"),
        ("caso_actualizado", "Caso actualizado"),
        ("caso_estatus", "Estatus de caso actualizado"),
        ("caso_eliminado", "Caso eliminado"),
        ("caso_mencion", "Mención en comentario de caso"),
        ("caso_tarea_asignada", "Tarea interna asignada"),
        ("caso_tarea_completada", "Tarea interna completada"),
        ("tramite_creado", "Trámite asociado creado"),
        ("tramite_actualizado", "Trámite asociado actualizado"),
        ("tramite_estatus", "Estatus de trámite actualizado"),
        ("tramite_eliminado", "Trámite asociado eliminado"),
        ("minuta_eliminada", "Minuta eliminada"),
        ("sla_alerta", "Alerta SLA"),
        ("sla_escalamiento", "Escalamiento SLA"),
        ("registro_leido", "Registro leído"),
    )

    evento = models.CharField(max_length=40, choices=EVENTO_CHOICES)
    titulo = models.CharField(max_length=255)
    mensaje = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="notificaciones_emitidas",
        blank=True,
        null=True,
        verbose_name="Generado por",
    )
    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.SET_NULL,
        related_name="notificaciones",
        blank=True,
        null=True,
        verbose_name="Caso",
    )
    tramite = models.ForeignKey(
        "TramiteCaso",
        on_delete=models.SET_NULL,
        related_name="notificaciones",
        blank=True,
        null=True,
        verbose_name="Trámite asociado",
    )
    referencia = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Referencia",
        help_text="Texto de referencia cuando el registro ya no existe.",
    )

    class Meta:
        ordering = ("-creado_en",)
        verbose_name = "Notificación (bandeja)"
        verbose_name_plural = "Notificaciones (bandeja)"

    def __str__(self) -> str:
        return f"{self.titulo} · {self.creado_en:%Y-%m-%d %H:%M}"


class BandejaNotificacionDestinatario(models.Model):
    """Destinatarios de una notificación y su estado de lectura."""

    notificacion = models.ForeignKey(
        BandejaNotificacion,
        on_delete=models.CASCADE,
        related_name="destinatarios",
        verbose_name="Notificación",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones_recibidas",
        verbose_name="Usuario",
    )
    leido = models.BooleanField(default=False)
    leido_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("notificacion", "usuario")
        verbose_name = "Destinatario de notificación"
        verbose_name_plural = "Destinatarios de notificaciones"


class FolioConsecutivo(models.Model):
    """Consecutivo anual para folios del expediente."""

    anio = models.PositiveIntegerField(db_index=True, verbose_name="Año")
    prefijo = models.CharField(max_length=255, verbose_name="Prefijo")
    ultimo_numero = models.PositiveIntegerField(default=0, verbose_name="Último número")
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="folios_actualizados",
    )

    class Meta:
        unique_together = (("anio", "prefijo"),)
        verbose_name = "Consecutivo de folio"
        verbose_name_plural = "Consecutivos de folio"

    def __str__(self) -> str:
        return f"{self.prefijo}/{self.ultimo_numero}/{self.anio}"


class FolioPrefijo(models.Model):
    """Prefijos de folios para expedientes."""

    nombre = models.CharField(max_length=255, unique=True)
    descripcion = models.TextField(blank=True)
    esta_activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre",)
        verbose_name = "Prefijo de folio"
        verbose_name_plural = "Prefijos de folio"

    def __str__(self) -> str:
        return self.nombre


class FolioRegistro(models.Model):
    """Registro de folios generados y su trazabilidad."""

    TIPO_CHOICES = (
        ("caso", "Caso"),
        ("tramite", "Trámite anexo"),
    )

    anio = models.PositiveIntegerField(db_index=True, verbose_name="Año")
    prefijo = models.CharField(max_length=255, verbose_name="Prefijo")
    numero = models.PositiveIntegerField(verbose_name="Número")
    folio = models.CharField(max_length=255, db_index=True, verbose_name="Folio completo")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    casos = models.ManyToManyField(
        CasoInterno,
        blank=True,
        related_name="folios_generados",
    )
    tramite = models.ForeignKey(
        "TramiteCaso",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="folios_generados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="folios_creados",
    )
    activo = models.BooleanField(default=True)
    eliminado_en = models.DateTimeField(blank=True, null=True)
    eliminado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="folios_eliminados",
    )
    notas = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("anio", "prefijo")),
        ]
        verbose_name = "Registro de folio"
        verbose_name_plural = "Registros de folio"

    def __str__(self) -> str:
        return self.folio


class FolioActividad(models.Model):
    """Bitácora de actividad sobre folios."""

    ACCION_CHOICES = (
        ("creado", "Creado"),
        ("editado", "Editado"),
        ("eliminado", "Eliminado"),
    )

    folio = models.ForeignKey(
        FolioRegistro,
        on_delete=models.CASCADE,
        related_name="actividades",
    )
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="folios_actividades",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    detalle = models.TextField(blank=True)

    class Meta:
        ordering = ("-creado_en",)
        verbose_name = "Actividad de folio"
        verbose_name_plural = "Actividades de folios"




class EstatusLicencia(CatalogoBase):
    """Catálogo de estatus para licencias."""

    orden = models.PositiveIntegerField(default=1)

    class Meta(CatalogoBase.Meta):
        ordering = ("orden", "nombre")
        verbose_name = "Estatus de licencia"
        verbose_name_plural = "Estatus de licencias"


class LicenciaRegistro(models.Model):
    """Registro y control de licencias del personal."""

    trabajador = models.ForeignKey(
        PlantillaEmpleado,
        on_delete=models.PROTECT,
        related_name="licencias",
        verbose_name="Trabajador",
    )
    trabajador_correo = models.EmailField(blank=True, verbose_name="Correo trabajador")
    trabajador_celular = models.CharField(max_length=50, blank=True, verbose_name="Celular trabajador")
    trabajador_sistema = models.CharField(max_length=255, blank=True, verbose_name="Federal/Estatal")
    tipo_tramite = models.CharField(
        max_length=30,
        choices=TIPO_LICENCIA_CHOICES,
        verbose_name="Licencia o trámite",
    )
    tipo_prorroga = models.CharField(
        max_length=30,
        choices=TIPO_PRORROGA_CHOICES,
        verbose_name="Trámite inicial o prórroga",
    )
    sindicato = models.CharField(
        max_length=30,
        choices=SINDICATO_CHOICES,
        verbose_name="Nombre del sindicato",
    )
    fecha_tramite = models.DateField(verbose_name="Fecha del trámite")
    numero_expediente = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Número de expediente (solicitud inicial)",
    )
    respuesta_oficio = models.CharField(
        max_length=50,
        choices=RESPUESTA_OFICIO_CHOICES,
        blank=True,
        verbose_name="Respuesta de oficio a",
    )
    respuesta_numero_expediente = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Número de expediente (respuesta)",
    )
    respuesta_fecha_recepcion = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de recepción (respuesta)",
    )
    visto_bueno = models.CharField(
        max_length=50,
        choices=VISTO_BUENO_CHOICES,
        blank=True,
        verbose_name="Visto bueno por",
    )
    visto_bueno_numero_expediente = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Número de expediente (visto bueno)",
    )
    visto_bueno_fecha = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de visto bueno",
    )
    fecha_recepcion_daf = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de recepción por la Subd. de Org. y Adm. de Personal - DAF",
    )
    aplica_estatal = models.BooleanField(
        default=False,
        verbose_name="Aplica para trámites estatales o prórrogas",
    )
    cita_valoracion = models.CharField(
        max_length=50,
        choices=CITA_VALORACION_CHOICES,
        blank=True,
        verbose_name="Cita de valoración o incidencia",
    )
    cita_valoracion_numero_expediente = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Número de expediente (cita/valoración)",
    )
    cita_valoracion_fecha = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de la cita de valoración del trabajador",
    )
    fecha_contacto = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de contacto al sindicato y al trabajador",
    )
    dictamen_numero_expediente = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Número de expediente del dictamen",
    )
    dictamen_fecha = models.DateField(blank=True, null=True, verbose_name="Fecha del dictamen")
    dictamen_periodo_de = models.DateField(blank=True, null=True, verbose_name="Periodo de")
    dictamen_periodo_hasta = models.DateField(blank=True, null=True, verbose_name="Periodo hasta")
    notificacion_numero_expediente = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Número de expediente de la notificación",
    )
    notificacion_fecha = models.DateField(blank=True, null=True, verbose_name="Fecha de la notificación")
    estatus = models.ForeignKey(
        EstatusLicencia,
        on_delete=models.PROTECT,
        related_name="licencias",
        verbose_name="Estatus",
        blank=True,
        null=True,
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="licencias_creadas",
        verbose_name="Registrado por",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-fecha_tramite", "-fecha_registro")
        indexes = [
            models.Index(fields=("trabajador",)),
            models.Index(fields=("estatus",)),
            models.Index(fields=("fecha_tramite",)),
        ]
        verbose_name = "Licencia"
        verbose_name_plural = "Licencias"

    def __str__(self) -> str:
        return f"{self.trabajador} · {self.get_tipo_tramite_display()} · {self.fecha_tramite}"


class HistorialEstatusLicencia(models.Model):
    """Bitácora de cambios de estatus en licencias."""

    licencia = models.ForeignKey(
        LicenciaRegistro,
        on_delete=models.CASCADE,
        related_name="historial_estatus",
        verbose_name="Licencia",
    )
    estatus_anterior = models.ForeignKey(
        EstatusLicencia,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        verbose_name="Estatus anterior",
    )
    estatus_nuevo = models.ForeignKey(
        EstatusLicencia,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="Estatus nuevo",
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de cambio")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="cambios_estatus_licencias",
        blank=True,
        null=True,
        verbose_name="Registrado por",
    )
    comentario = models.TextField(blank=True, verbose_name="Comentario")

    class Meta:
        ordering = ("-fecha_cambio",)
        verbose_name = "Historial de estatus de licencia"
        verbose_name_plural = "Historial de estatus de licencias"

    def __str__(self) -> str:
        return f"{self.licencia} · {self.estatus_anterior or '—'} → {self.estatus_nuevo}"


class MinutaCaso(models.Model):
    """Minutas adjuntas a un caso."""

    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.CASCADE,
        related_name="minutas_adjuntas",
        verbose_name="Caso",
    )
    archivo = models.FileField(
        upload_to="tramites/minutas/casos/",
        validators=[FileExtensionValidator(["pdf"])],
        verbose_name="Minuta (PDF)",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-creado_en",)
        verbose_name = "Minuta del caso"
        verbose_name_plural = "Minutas del caso"

    def __str__(self) -> str:
        return f"{self.caso} · {self.archivo.name}"


class MinutaTramite(models.Model):
    """Minutas adjuntas a un trámite del caso."""

    tramite = models.ForeignKey(
        TramiteCaso,
        on_delete=models.CASCADE,
        related_name="minutas_adjuntas",
        verbose_name="Trámite del caso",
    )
    archivo = models.FileField(
        upload_to="tramites/minutas/tramites/",
        validators=[FileExtensionValidator(["pdf"])],
        verbose_name="Minuta (PDF)",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-creado_en",)
        verbose_name = "Minuta del trámite"
        verbose_name_plural = "Minutas del trámite"

    def __str__(self) -> str:
        return f"{self.tramite} · {self.archivo.name}"


class FeatureFlag(models.Model):
    """Feature flag para habilitar módulos de forma gradual por rol/grupo."""

    codigo = models.SlugField(max_length=80, unique=True)
    modulo = models.CharField(max_length=80, db_index=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    habilitado = models.BooleanField(
        default=True,
        verbose_name="Habilitado globalmente",
        help_text="Si está desactivado, nadie puede usar este módulo.",
    )
    habilitado_por_defecto = models.BooleanField(
        default=True,
        verbose_name="Habilitado por defecto",
        help_text="Valor por defecto para usuarios sin regla por grupo.",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("modulo", "codigo")
        verbose_name = "Feature flag"
        verbose_name_plural = "Feature flags"

    def __str__(self) -> str:
        return f"{self.modulo} · {self.codigo}"


class FeatureFlagGrupo(models.Model):
    """Sobrescritura de feature flag por grupo/rol."""

    flag = models.ForeignKey(
        FeatureFlag,
        on_delete=models.CASCADE,
        related_name="asignaciones_grupo",
    )
    grupo = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="feature_flags",
    )
    habilitado = models.BooleanField(default=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="feature_flags_actualizados",
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("flag", "grupo"),)
        ordering = ("flag__modulo", "flag__codigo", "grupo__name")
        verbose_name = "Regla de feature flag por grupo"
        verbose_name_plural = "Reglas de feature flags por grupo"

    def __str__(self) -> str:
        return f"{self.flag.codigo} · {self.grupo.name} · {'ON' if self.habilitado else 'OFF'}"


class ScheduledJob(models.Model):
    """Definición de un job programado."""

    ESTADO_CHOICES = (
        ("pendiente", "Pendiente"),
        ("ejecutando", "Ejecutando"),
        ("exitoso", "Exitoso"),
        ("error", "Error"),
    )

    codigo = models.SlugField(max_length=80, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    handler = models.CharField(
        max_length=80,
        verbose_name="Handler del job",
        help_text="Nombre del handler registrado en la infraestructura de jobs.",
    )
    intervalo_minutos = models.PositiveIntegerField(default=60)
    activo = models.BooleanField(default=True)
    proxima_ejecucion = models.DateTimeField(default=timezone.now, db_index=True)
    ultima_ejecucion = models.DateTimeField(blank=True, null=True)
    ultimo_estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente")
    ultimo_error = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("codigo",)
        verbose_name = "Job programado"
        verbose_name_plural = "Jobs programados"

    def __str__(self) -> str:
        return f"{self.codigo} ({self.intervalo_minutos} min)"


class AsyncJob(models.Model):
    """Job en cola para ejecución asíncrona."""

    ESTADO_CHOICES = (
        ("pendiente", "Pendiente"),
        ("ejecutando", "Ejecutando"),
        ("exitoso", "Exitoso"),
        ("error", "Error"),
        ("cancelado", "Cancelado"),
    )

    job_type = models.CharField(max_length=80, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente", db_index=True)
    prioridad = models.PositiveSmallIntegerField(default=100, db_index=True)
    ejecutar_despues_de = models.DateTimeField(default=timezone.now, db_index=True)
    intentos = models.PositiveSmallIntegerField(default=0)
    max_intentos = models.PositiveSmallIntegerField(default=3)
    locked_by = models.CharField(max_length=100, blank=True)
    locked_en = models.DateTimeField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    iniciado_en = models.DateTimeField(blank=True, null=True)
    finalizado_en = models.DateTimeField(blank=True, null=True)
    error_mensaje = models.TextField(blank=True)
    resultado = models.JSONField(default=dict, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="jobs_creados",
    )
    scheduled_job = models.ForeignKey(
        ScheduledJob,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="jobs_ejecutados",
    )

    class Meta:
        ordering = ("-creado_en",)
        indexes = [
            models.Index(fields=("estado", "ejecutar_despues_de", "prioridad")),
            models.Index(fields=("job_type", "estado")),
        ]
        verbose_name = "Job asíncrono"
        verbose_name_plural = "Jobs asíncronos"

    def __str__(self) -> str:
        return f"{self.job_type} · {self.estado} · {self.creado_en:%Y-%m-%d %H:%M}"


class DataQualityRun(models.Model):
    """Ejecución del servicio de calidad de datos."""

    ORIGEN_CHOICES = (
        ("manual", "Manual"),
        ("programado", "Programado"),
        ("cli", "CLI"),
    )
    ESTADO_CHOICES = (
        ("ejecutando", "Ejecutando"),
        ("exitoso", "Exitoso"),
        ("error", "Error"),
    )

    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default="manual")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="ejecutando")
    iniciado_en = models.DateTimeField(auto_now_add=True)
    finalizado_en = models.DateTimeField(blank=True, null=True)
    ejecutado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="corridas_calidad_datos",
    )
    resumen = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    async_job = models.ForeignKey(
        AsyncJob,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="quality_runs",
    )

    class Meta:
        ordering = ("-iniciado_en",)
        verbose_name = "Corrida de calidad de datos"
        verbose_name_plural = "Corridas de calidad de datos"

    def __str__(self) -> str:
        return f"Run #{self.pk} · {self.estado} · {self.iniciado_en:%Y-%m-%d %H:%M}"


class DataQualityIssue(models.Model):
    """Hallazgo accionable del servicio de calidad de datos."""

    CATEGORIA_CHOICES = (
        ("incompleto", "Expediente incompleto"),
        ("duplicado", "Expediente duplicado"),
        ("inconsistente", "Dato inconsistente"),
    )
    SEVERIDAD_CHOICES = (
        ("baja", "Baja"),
        ("media", "Media"),
        ("alta", "Alta"),
    )
    ENTIDAD_CHOICES = (
        ("caso", "Caso"),
        ("tramite", "Trámite"),
        ("licencia", "Licencia"),
    )

    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, db_index=True)
    severidad = models.CharField(max_length=10, choices=SEVERIDAD_CHOICES, default="media")
    regla_codigo = models.CharField(max_length=80)
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    entidad_tipo = models.CharField(max_length=20, choices=ENTIDAD_CHOICES, db_index=True)
    entidad_id = models.PositiveIntegerField(db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    activo = models.BooleanField(default=True, db_index=True)
    primer_detectado_en = models.DateTimeField(auto_now_add=True)
    ultimo_detectado_en = models.DateTimeField(auto_now=True)
    resuelto_en = models.DateTimeField(blank=True, null=True)
    ultima_corrida = models.ForeignKey(
        DataQualityRun,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="issues",
    )
    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="quality_issues",
    )
    tramite = models.ForeignKey(
        TramiteCaso,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="quality_issues",
    )
    licencia = models.ForeignKey(
        LicenciaRegistro,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="quality_issues",
    )

    class Meta:
        ordering = ("-ultimo_detectado_en", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("categoria", "regla_codigo", "entidad_tipo", "entidad_id"),
                name="quality_issue_unica_por_regla",
            )
        ]
        indexes = [
            models.Index(fields=("activo", "categoria", "severidad")),
            models.Index(fields=("entidad_tipo", "entidad_id")),
        ]
        verbose_name = "Hallazgo de calidad de datos"
        verbose_name_plural = "Hallazgos de calidad de datos"

    def __str__(self) -> str:
        return f"{self.get_categoria_display()} · {self.entidad_tipo} #{self.entidad_id}"


class EventoSistema(models.Model):
    """Modelo unificado de eventos del dominio (casos, trámites, estatus, jobs)."""

    CATEGORIA_CHOICES = (
        ("caso", "Caso"),
        ("tramite", "Trámite"),
        ("licencia", "Licencia"),
        ("estatus", "Estatus"),
        ("job", "Job"),
        ("calidad_datos", "Calidad de datos"),
        ("feature_flag", "Feature flag"),
        ("sistema", "Sistema"),
    )
    ACCION_CHOICES = (
        ("creado", "Creado"),
        ("actualizado", "Actualizado"),
        ("eliminado", "Eliminado"),
        ("cambio_estatus", "Cambio de estatus"),
        ("ejecutado", "Ejecutado"),
        ("detectado", "Detectado"),
        ("habilitado", "Habilitado"),
        ("deshabilitado", "Deshabilitado"),
        ("error", "Error"),
    )

    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, db_index=True)
    accion = models.CharField(max_length=30, choices=ACCION_CHOICES, db_index=True)
    descripcion = models.CharField(max_length=255)
    detalle = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="eventos_sistema",
    )
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    request_id = models.CharField(max_length=64, blank=True)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="eventos_sistema",
    )
    object_id = models.PositiveIntegerField(blank=True, null=True, db_index=True)
    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="eventos_sistema",
    )
    tramite = models.ForeignKey(
        TramiteCaso,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="eventos_sistema",
    )
    licencia = models.ForeignKey(
        LicenciaRegistro,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="eventos_sistema",
    )

    class Meta:
        ordering = ("-creado_en", "-id")
        indexes = [
            models.Index(fields=("categoria", "accion", "creado_en")),
            models.Index(fields=("content_type", "object_id")),
        ]
        verbose_name = "Evento del sistema"
        verbose_name_plural = "Eventos del sistema"

    def __str__(self) -> str:
        return f"{self.get_categoria_display()} · {self.get_accion_display()} · {self.creado_en:%Y-%m-%d %H:%M}"


class BitacoraCambioCritico(models.Model):
    """Bitácora extendida de cambios críticos (antes/después)."""

    ACCION_CHOICES = (
        ("creado", "Creado"),
        ("actualizado", "Actualizado"),
        ("eliminado", "Eliminado"),
        ("cambio_estatus", "Cambio de estatus"),
        ("ejecutado", "Ejecutado"),
        ("habilitado", "Habilitado"),
        ("deshabilitado", "Deshabilitado"),
        ("error", "Error"),
    )

    modulo = models.CharField(max_length=50, db_index=True)
    accion = models.CharField(max_length=30, choices=ACCION_CHOICES, db_index=True)
    descripcion = models.CharField(max_length=255, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="bitacora_cambios_criticos",
    )
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    request_id = models.CharField(max_length=64, blank=True)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        related_name="bitacora_cambios_criticos",
    )
    object_id = models.PositiveIntegerField(db_index=True)
    objeto_repr = models.CharField(max_length=255, blank=True)
    antes = models.JSONField(default=dict, blank=True)
    despues = models.JSONField(default=dict, blank=True)
    cambios = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="bitacora_cambios_criticos",
    )
    tramite = models.ForeignKey(
        TramiteCaso,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="bitacora_cambios_criticos",
    )
    licencia = models.ForeignKey(
        LicenciaRegistro,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="bitacora_cambios_criticos",
    )

    class Meta:
        ordering = ("-creado_en", "-id")
        indexes = [
            models.Index(fields=("modulo", "accion", "creado_en")),
            models.Index(fields=("content_type", "object_id")),
            models.Index(fields=("actor", "creado_en")),
        ]
        verbose_name = "Bitácora de cambio crítico"
        verbose_name_plural = "Bitácora de cambios críticos"

    def __str__(self) -> str:
        return f"{self.modulo} · {self.get_accion_display()} · {self.creado_en:%Y-%m-%d %H:%M}"


class FiltroGuardadoUsuario(models.Model):
    """Filtro guardado por usuario para reutilizar búsquedas operativas."""

    ALCANCE_CASOS_LISTADO = "casos_listado"
    ALCANCE_COLA_TRABAJO = "cola_trabajo"
    ALCANCE_CHOICES = (
        (ALCANCE_CASOS_LISTADO, "Listado de trámites"),
        (ALCANCE_COLA_TRABAJO, "Mi cola de trabajo"),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="filtros_guardados_operacion",
    )
    alcance = models.CharField(
        max_length=40,
        choices=ALCANCE_CHOICES,
        default=ALCANCE_CASOS_LISTADO,
        db_index=True,
    )
    nombre = models.CharField(max_length=120)
    query_string = models.TextField(
        blank=True,
        help_text="Parámetros GET serializados (sin URL base).",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("alcance", "nombre", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("usuario", "alcance", "nombre"),
                name="filtro_guardado_usuario_nombre_unico",
            )
        ]
        indexes = [
            models.Index(fields=("usuario", "alcance")),
        ]
        verbose_name = "Filtro guardado por usuario"
        verbose_name_plural = "Filtros guardados por usuario"

    def __str__(self) -> str:
        return f"{self.usuario} · {self.get_alcance_display()} · {self.nombre}"


class SLARegla(models.Model):
    """Catálogo de SLA por tipo y estatus para casos y trámites."""

    AMBITO_CASO = "caso"
    AMBITO_TRAMITE = "tramite"
    AMBITO_CHOICES = (
        (AMBITO_CASO, "Caso"),
        (AMBITO_TRAMITE, "Trámite"),
    )

    nombre = models.CharField(
        max_length=160,
        blank=True,
        help_text="Etiqueta opcional para operación.",
    )
    ambito = models.CharField(max_length=20, choices=AMBITO_CHOICES, db_index=True)
    tipo_proceso = models.ForeignKey(
        TipoProceso,
        on_delete=models.CASCADE,
        related_name="sla_reglas",
        verbose_name="Tipo de trámite",
    )
    estatus_caso = models.ForeignKey(
        EstatusCaso,
        on_delete=models.CASCADE,
        related_name="sla_reglas",
        blank=True,
        null=True,
        verbose_name="Estatus de caso",
    )
    estatus_tramite = models.ForeignKey(
        EstatusTramite,
        on_delete=models.CASCADE,
        related_name="sla_reglas",
        blank=True,
        null=True,
        verbose_name="Estatus de trámite",
    )
    dias_objetivo = models.PositiveIntegerField(
        default=10,
        verbose_name="Días objetivo",
        help_text="Días máximos para el vencimiento del SLA.",
    )
    dias_alerta_amarilla = models.PositiveSmallIntegerField(
        default=2,
        verbose_name="Alerta amarilla (días)",
        help_text="Días previos al vencimiento para cambiar a amarillo.",
    )
    dias_escalamiento = models.PositiveSmallIntegerField(
        default=2,
        verbose_name="Escalamiento (días vencido)",
        help_text="Días de atraso para escalar por regla.",
    )
    peso_riesgo = models.PositiveSmallIntegerField(
        default=50,
        verbose_name="Peso base de riesgo",
        help_text="Ajuste base del cálculo de riesgo (1-100).",
    )
    grupo_escalamiento = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        related_name="sla_reglas_escalamiento",
        blank=True,
        null=True,
        verbose_name="Rol de escalamiento",
    )
    esta_activa = models.BooleanField(default=True, db_index=True)
    orden = models.PositiveSmallIntegerField(default=1)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("ambito", "tipo_proceso__nombre", "orden", "id")
        constraints = [
            models.CheckConstraint(
                check=Q(ambito="caso", estatus_tramite__isnull=True)
                | Q(ambito="tramite", estatus_caso__isnull=True),
                name="sla_regla_estatus_segun_ambito",
            ),
            models.UniqueConstraint(
                fields=("ambito", "tipo_proceso", "estatus_caso"),
                condition=Q(ambito="caso", estatus_caso__isnull=False),
                name="sla_regla_caso_tipo_estatus_unica",
            ),
            models.UniqueConstraint(
                fields=("ambito", "tipo_proceso"),
                condition=Q(
                    ambito="caso",
                    estatus_caso__isnull=True,
                ),
                name="sla_regla_caso_base_unica",
            ),
            models.UniqueConstraint(
                fields=("ambito", "tipo_proceso", "estatus_tramite"),
                condition=Q(ambito="tramite", estatus_tramite__isnull=False),
                name="sla_regla_tramite_tipo_estatus_unica",
            ),
            models.UniqueConstraint(
                fields=("ambito", "tipo_proceso"),
                condition=Q(
                    ambito="tramite",
                    estatus_tramite__isnull=True,
                ),
                name="sla_regla_tramite_base_unica",
            ),
        ]
        indexes = [
            models.Index(fields=("ambito", "tipo_proceso", "esta_activa")),
            models.Index(fields=("ambito", "estatus_caso", "esta_activa")),
            models.Index(fields=("ambito", "estatus_tramite", "esta_activa")),
        ]
        verbose_name = "Regla SLA"
        verbose_name_plural = "Reglas SLA"

    def __str__(self) -> str:
        estatus = self.estatus_caso or self.estatus_tramite
        estatus_txt = f" · {estatus}" if estatus else " · Base"
        ambito_txt = self.get_ambito_display()
        return f"{ambito_txt} · {self.tipo_proceso}{estatus_txt}"

    def clean(self):
        super().clean()
        if self.ambito == self.AMBITO_CASO:
            self.estatus_tramite = None
        elif self.ambito == self.AMBITO_TRAMITE:
            self.estatus_caso = None
        if self.peso_riesgo > 100:
            raise ValidationError({"peso_riesgo": "El peso de riesgo debe estar entre 1 y 100."})


class SLAAlertaRegistro(models.Model):
    """Registro idempotente de alertas SLA y escalamientos."""

    ALERTA_AMARILLA = "amarilla"
    ALERTA_ROJA = "roja"
    ALERTA_ESCALAMIENTO = "escalamiento"
    TIPO_ALERTA_CHOICES = (
        (ALERTA_AMARILLA, "Alerta amarilla"),
        (ALERTA_ROJA, "Alerta roja"),
        (ALERTA_ESCALAMIENTO, "Escalamiento"),
    )

    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.CASCADE,
        related_name="sla_alertas",
        blank=True,
        null=True,
    )
    tramite = models.ForeignKey(
        TramiteCaso,
        on_delete=models.CASCADE,
        related_name="sla_alertas",
        blank=True,
        null=True,
    )
    regla = models.ForeignKey(
        SLARegla,
        on_delete=models.SET_NULL,
        related_name="alertas_generadas",
        blank=True,
        null=True,
    )
    tipo_alerta = models.CharField(max_length=20, choices=TIPO_ALERTA_CHOICES, db_index=True)
    fecha_vencimiento = models.DateField(db_index=True)
    dias_restantes = models.IntegerField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    async_job = models.ForeignKey(
        AsyncJob,
        on_delete=models.SET_NULL,
        related_name="sla_alertas_registradas",
        blank=True,
        null=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-creado_en", "-id")
        constraints = [
            models.CheckConstraint(
                check=Q(caso__isnull=False, tramite__isnull=True)
                | Q(caso__isnull=True, tramite__isnull=False),
                name="sla_alerta_un_objetivo",
            ),
            models.UniqueConstraint(
                fields=("caso", "tipo_alerta", "fecha_vencimiento"),
                condition=Q(caso__isnull=False, tramite__isnull=True),
                name="sla_alerta_caso_unica",
            ),
            models.UniqueConstraint(
                fields=("tramite", "tipo_alerta", "fecha_vencimiento"),
                condition=Q(caso__isnull=True, tramite__isnull=False),
                name="sla_alerta_tramite_unica",
            ),
        ]
        indexes = [
            models.Index(fields=("tipo_alerta", "fecha_vencimiento")),
            models.Index(fields=("caso", "creado_en")),
            models.Index(fields=("tramite", "creado_en")),
        ]
        verbose_name = "Registro de alerta SLA"
        verbose_name_plural = "Registros de alertas SLA"

    def __str__(self) -> str:
        objetivo = f"Caso #{self.caso_id}" if self.caso_id else f"Trámite #{self.tramite_id}"
        return f"{objetivo} · {self.get_tipo_alerta_display()} · {self.fecha_vencimiento:%Y-%m-%d}"
