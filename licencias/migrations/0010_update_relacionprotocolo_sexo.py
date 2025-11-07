from django.db import migrations, models


def forwards(apps, schema_editor):
    RelacionProtocolo = apps.get_model("licencias", "RelacionProtocolo")
    HistoricalRelacionProtocolo = apps.get_model("licencias", "HistoricalRelacionProtocolo")

    RelacionProtocolo.objects.filter(sexo="M").update(sexo="H")
    RelacionProtocolo.objects.filter(sexo="F").update(sexo="M")
    HistoricalRelacionProtocolo.objects.filter(sexo="M").update(sexo="H")
    HistoricalRelacionProtocolo.objects.filter(sexo="F").update(sexo="M")


def backwards(apps, schema_editor):
    RelacionProtocolo = apps.get_model("licencias", "RelacionProtocolo")
    HistoricalRelacionProtocolo = apps.get_model("licencias", "HistoricalRelacionProtocolo")

    RelacionProtocolo.objects.filter(sexo="H").update(sexo="M")
    RelacionProtocolo.objects.filter(sexo="M").update(sexo="F")
    HistoricalRelacionProtocolo.objects.filter(sexo="H").update(sexo="M")
    HistoricalRelacionProtocolo.objects.filter(sexo="M").update(sexo="F")


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0009_controlinternostatushistory"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalrelacionprotocolo",
            name="sexo",
            field=models.CharField(
                choices=[("H", "Hombre"), ("M", "Mujer"), ("X", "No especificado")],
                default="M",
                max_length=1,
                verbose_name="Sexo",
            ),
        ),
        migrations.AlterField(
            model_name="relacionprotocolo",
            name="sexo",
            field=models.CharField(
                choices=[("H", "Hombre"), ("M", "Mujer"), ("X", "No especificado")],
                default="M",
                max_length=1,
                verbose_name="Sexo",
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
