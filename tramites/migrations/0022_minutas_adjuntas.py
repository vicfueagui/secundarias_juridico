from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0021_minutas_history"),
    ]

    operations = [
        migrations.CreateModel(
            name="MinutaCaso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "archivo",
                    models.FileField(
                        upload_to="tramites/minutas/casos/",
                        validators=[django.core.validators.FileExtensionValidator(["pdf"])],
                        verbose_name="Minuta (PDF)",
                    ),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "caso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="minutas_adjuntas",
                        to="licencias.casointerno",
                        verbose_name="Caso",
                    ),
                ),
            ],
            options={
                "verbose_name": "Minuta del caso",
                "verbose_name_plural": "Minutas del caso",
                "ordering": ("-creado_en",),
            },
        ),
        migrations.CreateModel(
            name="MinutaTramite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "archivo",
                    models.FileField(
                        upload_to="tramites/minutas/tramites/",
                        validators=[django.core.validators.FileExtensionValidator(["pdf"])],
                        verbose_name="Minuta (PDF)",
                    ),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "tramite",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="minutas_adjuntas",
                        to="licencias.tramitecaso",
                        verbose_name="Trámite del caso",
                    ),
                ),
            ],
            options={
                "verbose_name": "Minuta del trámite",
                "verbose_name_plural": "Minutas del trámite",
                "ordering": ("-creado_en",),
            },
        ),
    ]
