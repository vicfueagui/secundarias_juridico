from __future__ import annotations

from django.db import migrations, models
from django.db.models import Q


def forwards_create_ccts(apps, schema_editor):
    CasoInterno = apps.get_model("licencias", "CasoInterno")
    CCTSecundaria = apps.get_model("licencias", "CCTSecundaria")
    PlantillaCentroTrabajo = apps.get_model("licencias", "PlantillaCentroTrabajo")

    existing = set(PlantillaCentroTrabajo.objects.values_list("cct", flat=True))
    casos = (
        CasoInterno.objects.exclude(cct_id__isnull=True)
        .exclude(cct_id="")
        .values_list("cct_id", "cct_nombre", "asesor_cct", "cct_sistema", "cct_modalidad")
        .distinct()
    )

    for cct_id, cct_nombre, asesor_cct, cct_sistema, cct_modalidad in casos:
        if not cct_id or cct_id in existing:
            continue
        origen = CCTSecundaria.objects.filter(cct=cct_id).first()
        PlantillaCentroTrabajo.objects.create(
            cct=cct_id,
            nombre=(getattr(origen, "nombre", "") or cct_nombre or "Sin nombre"),
            municipio=getattr(origen, "municipio", "") or "",
            asesor=(getattr(origen, "asesor", "") or asesor_cct or ""),
            sostenimiento=(getattr(origen, "sostenimiento", "") or cct_sistema or ""),
            subnivel=(getattr(origen, "servicio", "") or cct_modalidad or ""),
            turno=getattr(origen, "turno", "") or "",
        )
        existing.add(cct_id)


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0035_merge_20260205_1512"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plantillaregistro",
            name="origen_id",
            field=models.PositiveIntegerField(blank=True, null=True, unique=True, verbose_name="ID de origen"),
        ),
        migrations.CreateModel(
            name="CasoTrabajador",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("es_principal", models.BooleanField(default=False, verbose_name="Trabajador principal")),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                (
                    "caso",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="trabajadores_caso", to="licencias.casointerno"),
                ),
                (
                    "centro_trabajo_preferido",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="trabajadores_preferidos",
                        to="licencias.plantillacentrotrabajo",
                        verbose_name="Centro de trabajo preferido",
                    ),
                ),
                (
                    "trabajador",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="casos_trabajador",
                        to="licencias.plantillaempleado",
                    ),
                ),
            ],
            options={
                "verbose_name": "Trabajador del caso",
                "verbose_name_plural": "Trabajadores del caso",
                "ordering": ("-creado_en",),
            },
        ),
        migrations.AddConstraint(
            model_name="casotrabajador",
            constraint=models.UniqueConstraint(
                condition=Q(("es_principal", True)),
                fields=("caso",),
                name="caso_un_trabajador_principal",
            ),
        ),
        migrations.AddConstraint(
            model_name="casotrabajador",
            constraint=models.UniqueConstraint(fields=("caso", "trabajador"), name="caso_trabajador_unico"),
        ),
        migrations.AddField(
            model_name="casointerno",
            name="trabajadores",
            field=models.ManyToManyField(
                blank=True,
                related_name="casos_tramites",
                through="licencias.CasoTrabajador",
                to="licencias.plantillaempleado",
                verbose_name="Trabajadores vinculados",
            ),
        ),
        migrations.RunPython(forwards_create_ccts, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="casointerno",
            name="cct",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="casos",
                to="licencias.plantillacentrotrabajo",
                verbose_name="CCT principal",
            ),
        ),
        migrations.AddIndex(
            model_name="plantillaregistro",
            index=models.Index(
                fields=["empleado", "anio", "ciclo"],
                name="plantilla_reg_empleado_anio_ciclo_idx",
            ),
        ),
    ]
