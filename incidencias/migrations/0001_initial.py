from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Incidencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero", models.CharField(max_length=20, unique=True, verbose_name="No.")),
                ("apellido_paterno", models.CharField(max_length=50)),
                ("apellido_materno", models.CharField(blank=True, max_length=50)),
                ("nombres", models.CharField(max_length=100)),
                ("rfc", models.CharField(max_length=13, verbose_name="R.F.C")),
                ("filiacion", models.CharField(blank=True, max_length=50)),
                ("cct", models.CharField(max_length=20, verbose_name="C.C.T")),
                ("numero_serie", models.CharField(blank=True, max_length=50, verbose_name="No. serie")),
                ("dias", models.PositiveIntegerField(verbose_name="Días")),
                ("fecha_del", models.DateField(verbose_name="Del")),
                ("fecha_al", models.DateField(verbose_name="Al")),
                (
                    "cuerpo_personalizado",
                    models.TextField(
                        blank=True,
                        help_text="Si se deja vacío, se usará la plantilla por defecto configurada en admin.",
                        verbose_name="Cuerpo del reporte (editable)",
                    ),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Incidencia",
                "verbose_name_plural": "Incidencias",
                "ordering": ("-creado_en",),
            },
        ),
        migrations.CreateModel(
            name="PlantillaReporteIncidencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(default="Incidencias", max_length=100)),
                ("logo", models.ImageField(blank=True, null=True, upload_to="logos/")),
                (
                    "titulo",
                    models.CharField(
                        default="RELACIÓN DE LICENCIAS MÉDICAS CORRESPONDIENTES AL PERSONAL DE BASE A DISPOSICIÓN (PROTOCOLO)",
                        max_length=200,
                    ),
                ),
                (
                    "cuerpo_base",
                    models.TextField(
                        default="Por medio de la presente se informa que {{ nombre_completo }} con RFC {{ rfc }} cuenta con {{ dias }} días de licencia médica {{ fecha_rango }}.",
                        help_text="Texto base del reporte. Puedes usar variables como {{ nombre_completo }}.",
                    ),
                ),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Plantilla de reporte de incidencia",
                "verbose_name_plural": "Plantillas de reporte de incidencias",
            },
        ),
    ]
