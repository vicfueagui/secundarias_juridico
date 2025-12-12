from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0011_historial_estatus_tramite_caso"),
    ]

    operations = [
        migrations.AddField(
            model_name="casointerno",
            name="fecha_termino",
            field=models.DateField(blank=True, null=True, verbose_name="Fecha de término"),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="fecha_termino",
            field=models.DateField(blank=True, null=True, verbose_name="Fecha de término"),
        ),
    ]
