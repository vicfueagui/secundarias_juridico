from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0012_fecha_termino_tramites"),
    ]

    operations = [
        migrations.AddField(
            model_name="destinatario",
            name="funcion",
            field=models.CharField(blank=True, max_length=255, verbose_name="Función"),
        ),
        migrations.AddField(
            model_name="solicitante",
            name="funcion",
            field=models.CharField(blank=True, max_length=255, verbose_name="Función"),
        ),
    ]
