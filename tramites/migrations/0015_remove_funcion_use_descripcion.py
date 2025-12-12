from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0014_historicalcasointerno_fecha_termino_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="destinatario",
            name="funcion",
        ),
        migrations.RemoveField(
            model_name="solicitante",
            name="funcion",
        ),
        migrations.RemoveField(
            model_name="historicaldestinatario",
            name="funcion",
        ),
        migrations.RemoveField(
            model_name="historicalsolicitante",
            name="funcion",
        ),
    ]
