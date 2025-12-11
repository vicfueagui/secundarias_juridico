"""Modelos principales del módulo de trámites."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

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
    history = HistoricalRecords()
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("cct",)
        verbose_name = "Centro de trabajo (Secundaria)"
        verbose_name_plural = "Centros de trabajo (Secundaria)"

    def __str__(self) -> str:
        return f"{self.cct} · {self.nombre}"


class TipoProceso(CatalogoBase):
    """Catálogo de tipos de trámite utilizados en el registro."""

    es_documento = models.BooleanField(
        default=False,
        help_text="Indica si requiere documentos adicionales.",
    )

    class Meta(CatalogoBase.Meta):
        verbose_name = "Tipo de trámite"
        verbose_name_plural = "Tipos de trámite"


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


class Destinatario(CatalogoBase):
    """Catálogo de destinatarios (dirigido a)."""

    class Meta(CatalogoBase.Meta):
        verbose_name = "Destinatario"
        verbose_name_plural = "Destinatarios"


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


class CasoInterno(models.Model):
    """Trámite registrado para cada centro de trabajo."""

    cct = models.ForeignKey(
        CCTSecundaria,
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
    numero_oficio = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Número de expediente",
    )
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
        if self.cct:
            self.cct_nombre = self.cct.nombre
            self.cct_sistema = normalise_sistema(self.cct.sostenimiento)
            self.cct_modalidad = self.cct.servicio or ""
            if not self.asesor_cct:
                self.asesor_cct = self.cct.asesor
        self.cct_sistema = normalise_sistema(self.cct_sistema)


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


class TramiteCaso(models.Model):
    """Trámites adicionales asociados a un caso para seguimiento."""

    caso = models.ForeignKey(
        CasoInterno,
        on_delete=models.CASCADE,
        related_name="tramites_relacionados",
        verbose_name="Caso",
    )
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
    numero_oficio = models.CharField(max_length=150, blank=True, verbose_name="Número de oficio")
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
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ("-fecha", "-creado_en")
        verbose_name = "Trámite del caso"
        verbose_name_plural = "Trámites del caso"

    def __str__(self) -> str:
        return f"{self.caso} · {self.tipo} · {self.fecha}"
