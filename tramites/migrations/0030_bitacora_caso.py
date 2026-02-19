from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("licencias", "0029_folios"),
    ]

    operations = [
        migrations.CreateModel(
            name="BitacoraCaso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "accion",
                    models.CharField(
                        choices=[
                            ("convertir_anexo", "Convertir a trámite anexo"),
                            ("unir_casos", "Unir casos"),
                        ],
                        max_length=50,
                    ),
                ),
                ("detalle", models.TextField(blank=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "caso_destino",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="bitacoras_destino",
                        to="licencias.casointerno",
                    ),
                ),
                (
                    "caso_origen",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="bitacoras_origen",
                        to="licencias.casointerno",
                    ),
                ),
                (
                    "tramite",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="bitacoras",
                        to="licencias.tramitecaso",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="bitacoras_casos",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Bitácora de caso",
                "verbose_name_plural": "Bitácoras de caso",
                "ordering": ("-creado_en",),
            },
        ),
    ]
