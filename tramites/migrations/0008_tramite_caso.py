from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0007_participantes_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="TramiteCaso",
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
                ("fecha", models.DateField(verbose_name="Fecha del trámite")),
                (
                    "numero_oficio",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="Número de oficio"
                    ),
                ),
                (
                    "asunto",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Asunto"
                    ),
                ),
                (
                    "observaciones",
                    models.TextField(blank=True, verbose_name="Observaciones"),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                (
                    "caso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tramites_relacionados",
                        to="licencias.casointerno",
                        verbose_name="Caso",
                    ),
                ),
                (
                    "estatus",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tramites_caso",
                        to="licencias.estatuscaso",
                        verbose_name="Estatus",
                    ),
                ),
                (
                    "tipo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tramites_caso",
                        to="licencias.tipoproceso",
                        verbose_name="Tipo de trámite",
                    ),
                ),
            ],
            options={
                "verbose_name": "Trámite del caso",
                "verbose_name_plural": "Trámites del caso",
                "ordering": ("-fecha", "-creado_en"),
            },
        ),
        migrations.CreateModel(
            name="HistoricalTramiteCaso",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("fecha", models.DateField(verbose_name="Fecha del trámite")),
                (
                    "numero_oficio",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="Número de oficio"
                    ),
                ),
                (
                    "asunto",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Asunto"
                    ),
                ),
                (
                    "observaciones",
                    models.TextField(blank=True, verbose_name="Observaciones"),
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
                    "caso",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="licencias.casointerno",
                        verbose_name="Caso",
                    ),
                ),
                (
                    "estatus",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="licencias.estatuscaso",
                        verbose_name="Estatus",
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
                (
                    "tipo",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="licencias.tipoproceso",
                        verbose_name="Tipo de trámite",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Trámite del caso",
                "verbose_name_plural": "historical Trámites del caso",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
