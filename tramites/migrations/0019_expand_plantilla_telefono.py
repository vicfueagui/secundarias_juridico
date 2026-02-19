from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0018_expand_plantilla_telefono_celular"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plantillaempleado",
            name="telefono",
            field=models.CharField(blank=True, max_length=255, verbose_name="Teléfono"),
        ),
    ]
