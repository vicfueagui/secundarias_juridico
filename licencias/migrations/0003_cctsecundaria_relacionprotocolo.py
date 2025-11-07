from __future__ import annotations

import datetime

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0002_historicaltramite_autorizado_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CCTSecundaria",
            fields=[
                (
                    "cct",
                    models.CharField(
                        help_text="Clave de centro de trabajo",
                        max_length=12,
                        primary_key=True,
                        serialize=False,
                        verbose_name="CCT",
                    ),
                ),
                (
                    "nombre",
                    models.CharField(
                        max_length=255,
                        verbose_name="Nombre de la escuela",
                    ),
                ),
                (
                    "asesor",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Asesor jurídico asignado",
                    ),
                ),
                (
                    "municipio",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Municipio",
                    ),
                ),
                (
                    "turno",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Turno",
                    ),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("cct",),
                "verbose_name": "Centro de trabajo (Secundaria)",
                "verbose_name_plural": "Centros de trabajo (Secundaria)",
            },
        ),
        migrations.CreateModel(
            name="RelacionProtocolo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "numero_registro",
                    models.PositiveIntegerField(
                        help_text="Identificador correlativo utilizado en el control vigente",
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                (
                    "fecha_inicio",
                    models.DateField(verbose_name="Fecha de inicio"),
                ),
                (
                    "iniciales",
                    models.CharField(max_length=50, verbose_name="Iniciales del NNA"),
                ),
                (
                    "nombre_nna",
                    models.CharField(max_length=255, verbose_name="Nombre del NNA"),
                ),
                (
                    "sexo",
                    models.CharField(
                        choices=[
                            ("F", "Femenino"),
                            ("M", "Masculino"),
                            ("X", "No especificado"),
                        ],
                        default="X",
                        max_length=1,
                        verbose_name="Sexo",
                    ),
                ),
                (
                    "escuela",
                    models.CharField(max_length=255, verbose_name="Escuela"),
                ),
                (
                    "tipo_violencia",
                    models.CharField(
                        max_length=255, verbose_name="Tipo de violencia"
                    ),
                ),
                (
                    "descripcion",
                    models.TextField(blank=True, verbose_name="Descripción"),
                ),
                (
                    "asesor_juridico",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Nombre del asesor jurídico",
                    ),
                ),
                (
                    "estatus",
                    models.CharField(
                        choices=[
                            ("activo", "Activo"),
                            ("seguimiento", "En seguimiento"),
                            ("cerrado", "Cerrado"),
                            ("cancelado", "Cancelado"),
                        ],
                        default="activo",
                        max_length=20,
                        verbose_name="Estatus",
                    ),
                ),
                (
                    "comentarios",
                    models.TextField(blank=True, verbose_name="Comentarios"),
                ),
                (
                    "anio",
                    models.PositiveIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(2000),
                            django.core.validators.MaxValueValidator(
                                datetime.date.today().year + 1
                            ),
                        ],
                        verbose_name="Año",
                    ),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                (
                    "cct",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="protocolos",
                        to="licencias.cctsecundaria",
                        verbose_name="CCT",
                    ),
                ),
            ],
            options={
                "ordering": ("-fecha_inicio", "-numero_registro"),
                "verbose_name": "Relación de Protocolo",
                "verbose_name_plural": "Relaciones de Protocolos",
            },
        ),
        migrations.CreateModel(
            name="HistoricalRelacionProtocolo",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                (
                    "numero_registro",
                    models.PositiveIntegerField(
                        blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("fecha_inicio", models.DateField(blank=True, null=True)),
                (
                    "iniciales",
                    models.CharField(max_length=50, verbose_name="Iniciales del NNA"),
                ),
                (
                    "nombre_nna",
                    models.CharField(max_length=255, verbose_name="Nombre del NNA"),
                ),
                (
                    "sexo",
                    models.CharField(
                        choices=[
                            ("F", "Femenino"),
                            ("M", "Masculino"),
                            ("X", "No especificado"),
                        ],
                        default="X",
                        max_length=1,
                        verbose_name="Sexo",
                    ),
                ),
                ("escuela", models.CharField(max_length=255, verbose_name="Escuela")),
                (
                    "tipo_violencia",
                    models.CharField(
                        max_length=255, verbose_name="Tipo de violencia"
                    ),
                ),
                (
                    "descripcion",
                    models.TextField(blank=True, verbose_name="Descripción"),
                ),
                (
                    "asesor_juridico",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Nombre del asesor jurídico",
                    ),
                ),
                (
                    "estatus",
                    models.CharField(
                        choices=[
                            ("activo", "Activo"),
                            ("seguimiento", "En seguimiento"),
                            ("cerrado", "Cerrado"),
                            ("cancelado", "Cancelado"),
                        ],
                        default="activo",
                        max_length=20,
                        verbose_name="Estatus",
                    ),
                ),
                (
                    "comentarios",
                    models.TextField(blank=True, verbose_name="Comentarios"),
                ),
                (
                    "anio",
                    models.PositiveIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(2000),
                            django.core.validators.MaxValueValidator(
                                datetime.date.today().year + 1
                            ),
                        ],
                        verbose_name="Año",
                    ),
                ),
                ("creado_en", models.DateTimeField(blank=True, editable=False)),
                ("actualizado_en", models.DateTimeField(blank=True, editable=False)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "cct",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="licencias.cctsecundaria",
                        verbose_name="CCT",
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Relación de Protocolo",
                "verbose_name_plural": "historical Relaciones de Protocolos",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalCCTSecundaria",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                (
                    "cct",
                    models.CharField(
                        db_index=True,
                        help_text="Clave de centro de trabajo",
                        max_length=12,
                        verbose_name="CCT",
                    ),
                ),
                (
                    "nombre",
                    models.CharField(
                        max_length=255,
                        verbose_name="Nombre de la escuela",
                    ),
                ),
                (
                    "asesor",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Asesor jurídico asignado",
                    ),
                ),
                (
                    "municipio",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Municipio",
                    ),
                ),
                (
                    "turno",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="Turno",
                    ),
                ),
                ("creado_en", models.DateTimeField(blank=True, editable=False)),
                ("actualizado_en", models.DateTimeField(blank=True, editable=False)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Centro de trabajo (Secundaria)",
                "verbose_name_plural": "historical Centros de trabajo (Secundaria)",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AddIndex(
            model_name="relacionprotocolo",
            index=models.Index(
                fields=["numero_registro"], name="licencias_re_numero__4a0dc6_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="relacionprotocolo",
            index=models.Index(fields=["anio"], name="licencias_re_anio_d3dce3_idx"),
        ),
        migrations.AddIndex(
            model_name="relacionprotocolo",
            index=models.Index(fields=["estatus"], name="licencias_re_estatus_471361_idx"),
        ),
        migrations.AddIndex(
            model_name="relacionprotocolo",
            index=models.Index(fields=["cct"], name="licencias_re_cct_e51b07_idx"),
        ),
    ]
