from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0017_plantillas_secundarias"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plantillaempleado",
            name="telefono",
            field=models.CharField(blank=True, max_length=50, verbose_name="Teléfono"),
        ),
        migrations.AlterField(
            model_name="plantillaempleado",
            name="celular",
            field=models.CharField(blank=True, max_length=50, verbose_name="Celular"),
        ),
    ]
