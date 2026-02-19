from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0016_casointerno_incidencia_afiliacion_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlantillaCentroTrabajo",
            fields=[
                ("cct", models.CharField(max_length=12, primary_key=True, serialize=False, verbose_name="CCT")),
                ("nombre", models.CharField(max_length=255, verbose_name="Nombre del centro de trabajo")),
                ("municipio", models.CharField(blank=True, max_length=255, verbose_name="Municipio")),
                ("asesor", models.CharField(blank=True, max_length=255, verbose_name="Asesor jurídico")),
                ("sostenimiento", models.CharField(blank=True, max_length=255, verbose_name="Sostenimiento")),
                ("subnivel", models.CharField(blank=True, max_length=255, verbose_name="Subnivel")),
                ("turno", models.CharField(blank=True, max_length=255, verbose_name="Turno")),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Centro de trabajo (Plantilla secundaria)",
                "verbose_name_plural": "Centros de trabajo (Plantilla secundaria)",
                "ordering": ("cct",),
            },
        ),
        migrations.CreateModel(
            name="PlantillaEmpleado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=255, verbose_name="Nombre del empleado")),
                ("rfc", models.CharField(blank=True, db_index=True, max_length=13, null=True, unique=True)),
                ("curp", models.CharField(blank=True, db_index=True, max_length=18, null=True, unique=True)),
                ("correo", models.EmailField(blank=True, max_length=254, verbose_name="Correo")),
                ("telefono", models.CharField(blank=True, max_length=20, verbose_name="Teléfono")),
                ("celular", models.CharField(blank=True, max_length=20, verbose_name="Celular")),
                ("direccion", models.CharField(blank=True, max_length=255, verbose_name="Dirección")),
                ("colonia", models.CharField(blank=True, max_length=255, verbose_name="Colonia")),
                ("codigo_postal", models.CharField(blank=True, max_length=10, verbose_name="Código postal")),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Empleado (Plantilla secundaria)",
                "verbose_name_plural": "Empleados (Plantilla secundaria)",
                "ordering": ("nombre",),
            },
        ),
        migrations.CreateModel(
            name="PlantillaRegistro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origen_id", models.PositiveIntegerField(unique=True, verbose_name="ID de origen")),
                ("situacion", models.CharField(blank=True, max_length=255, verbose_name="Situación")),
                ("funcion", models.CharField(blank=True, max_length=255, verbose_name="Función")),
                ("grado_grupo_horas", models.CharField(blank=True, max_length=255, verbose_name="Grado/Grupo/Horas")),
                ("ciclo", models.CharField(blank=True, max_length=20, verbose_name="Ciclo escolar")),
                ("anio", models.PositiveSmallIntegerField(blank=True, db_index=True, null=True, verbose_name="Año")),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                (
                    "centro_trabajo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registros",
                        to="licencias.plantillacentrotrabajo",
                    ),
                ),
                (
                    "empleado",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registros",
                        to="licencias.plantillaempleado",
                    ),
                ),
            ],
            options={
                "verbose_name": "Registro de plantilla (Secundaria)",
                "verbose_name_plural": "Registros de plantilla (Secundaria)",
                "ordering": ("-anio", "-ciclo", "empleado"),
                "indexes": [
                    models.Index(fields=["ciclo"], name="plantilla_ciclo_idx"),
                    models.Index(fields=["empleado", "anio"], name="plantilla_empleado_anio_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="PlantillaClavePresupuestal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("clave", models.CharField(max_length=128, verbose_name="Clave presupuestal")),
                (
                    "registro",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="claves",
                        to="licencias.plantillaregistro",
                    ),
                ),
            ],
            options={
                "verbose_name": "Clave presupuestal (Plantilla)",
                "verbose_name_plural": "Claves presupuestales (Plantilla)",
                "unique_together": {("registro", "clave")},
            },
        ),
    ]
