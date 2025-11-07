from __future__ import annotations

import datetime

from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0003_cctsecundaria_relacionprotocolo"),
    ]

    operations = [
        migrations.AddField(
            model_name="cctsecundaria",
            name="servicio",
            field=models.CharField(
                blank=True,
                help_text="Valor tomado del catálogo tiponivelsub_c_servicion3.",
                max_length=255,
                verbose_name="Servicio educativo (tiponivelsub_c_servicion3)",
            ),
        ),
        migrations.AddField(
            model_name="historicalcctsecundaria",
            name="servicio",
            field=models.CharField(
                blank=True,
                help_text="Valor tomado del catálogo tiponivelsub_c_servicion3.",
                max_length=255,
                verbose_name="Servicio educativo (tiponivelsub_c_servicion3)",
            ),
        ),
        migrations.CreateModel(
            name="ControlInterno",
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
                    "memorandum",
                    models.CharField(
                        help_text="Identificador del memorándum asociado.",
                        max_length=150,
                        verbose_name="Memorándum",
                    ),
                ),
                (
                    "fecha_memorandum",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="Fecha del memorándum",
                    ),
                ),
                (
                    "anio",
                    models.PositiveIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(2000),
                            django.core.validators.MaxValueValidator(
                                datetime.date.today().year + 2
                            ),
                        ],
                        verbose_name="Año",
                    ),
                ),
                (
                    "numero_interno",
                    models.CharField(max_length=100, verbose_name="Número interno"),
                ),
                ("asunto", models.CharField(max_length=255, verbose_name="Asunto")),
                (
                    "cct_nombre",
                    models.CharField(
                        max_length=255,
                        verbose_name="Nombre del centro de trabajo",
                    ),
                ),
                (
                    "tiponivelsub_c_servicion3",
                    models.CharField(
                        help_text="Servicio educativo asociado al CCT.",
                        max_length=255,
                        verbose_name="tiponivelsub_c_servicion3",
                    ),
                ),
                (
                    "fecha_contestacion",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="Fecha de contestación",
                    ),
                ),
                (
                    "numero_oficio_contestacion",
                    models.CharField(
                        blank=True,
                        max_length=150,
                        verbose_name="Número de oficio de contestación",
                    ),
                ),
                (
                    "asesor",
                    models.CharField(blank=True, max_length=255, verbose_name="Asesor"),
                ),
                (
                    "observaciones",
                    models.TextField(blank=True, verbose_name="Observaciones"),
                ),
                ("estatus", models.CharField(blank=True, max_length=150, verbose_name="Estatus")),
                (
                    "comentarios",
                    models.TextField(blank=True, verbose_name="Comentarios"),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                (
                    "cct",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="controles_internos",
                        to="licencias.cctsecundaria",
                        verbose_name="CCT",
                    ),
                ),
            ],
            options={
                "ordering": ("-fecha_memorandum", "-numero_interno"),
                "verbose_name": "Control de interno",
                "verbose_name_plural": "Control de internos",
                "indexes": [
                    models.Index(fields=["memorandum"], name="idx_controlinterno_memo"),
                    models.Index(fields=["anio"], name="idx_controlinterno_anio"),
                    models.Index(fields=["cct"], name="idx_controlinterno_cct"),
                    models.Index(fields=["estatus"], name="idx_controlinterno_estatus"),
                ],
            },
        ),
        migrations.CreateModel(
            name="HistoricalControlInterno",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                (
                    "memorandum",
                    models.CharField(
                        help_text="Identificador del memorándum asociado.",
                        max_length=150,
                        verbose_name="Memorándum",
                    ),
                ),
                (
                    "fecha_memorandum",
                    models.DateField(blank=True, null=True, verbose_name="Fecha del memorándum"),
                ),
                (
                    "anio",
                    models.PositiveIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(2000),
                            django.core.validators.MaxValueValidator(
                                datetime.date.today().year + 2
                            ),
                        ],
                        verbose_name="Año",
                    ),
                ),
                (
                    "numero_interno",
                    models.CharField(db_index=True, max_length=100, verbose_name="Número interno"),
                ),
                ("asunto", models.CharField(max_length=255, verbose_name="Asunto")),
                (
                    "cct_nombre",
                    models.CharField(
                        max_length=255,
                        verbose_name="Nombre del centro de trabajo",
                    ),
                ),
                (
                    "tiponivelsub_c_servicion3",
                    models.CharField(
                        help_text="Servicio educativo asociado al CCT.",
                        max_length=255,
                        verbose_name="tiponivelsub_c_servicion3",
                    ),
                ),
                (
                    "fecha_contestacion",
                    models.DateField(blank=True, null=True, verbose_name="Fecha de contestación"),
                ),
                (
                    "numero_oficio_contestacion",
                    models.CharField(
                        blank=True,
                        max_length=150,
                        verbose_name="Número de oficio de contestación",
                    ),
                ),
                (
                    "asesor",
                    models.CharField(blank=True, max_length=255, verbose_name="Asesor"),
                ),
                (
                    "observaciones",
                    models.TextField(blank=True, verbose_name="Observaciones"),
                ),
                ("estatus", models.CharField(blank=True, max_length=150, verbose_name="Estatus")),
                (
                    "comentarios",
                    models.TextField(blank=True, verbose_name="Comentarios"),
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
                "verbose_name": "historical Control de interno",
                "verbose_name_plural": "historical Control de internos",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
