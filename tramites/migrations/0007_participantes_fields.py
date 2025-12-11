from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0006_solicitante_destinatario"),
    ]

    operations = [
        migrations.AddField(
            model_name="casointerno",
            name="generador_iniciales",
            field=models.CharField(blank=True, max_length=50, verbose_name="Iniciales del NNA (generador)"),
        ),
        migrations.AddField(
            model_name="casointerno",
            name="generador_nombre",
            field=models.CharField(blank=True, max_length=255, verbose_name="Nombre del generador"),
        ),
        migrations.AddField(
            model_name="casointerno",
            name="generador_sexo",
            field=models.CharField(
                blank=True,
                choices=[("M", "Mujer"), ("H", "Hombre")],
                max_length=1,
                verbose_name="Sexo del NNA (generador)",
            ),
        ),
        migrations.AddField(
            model_name="casointerno",
            name="receptor_iniciales",
            field=models.CharField(blank=True, max_length=50, verbose_name="Iniciales del NNA (receptor)"),
        ),
        migrations.AddField(
            model_name="casointerno",
            name="receptor_nombre",
            field=models.CharField(blank=True, max_length=255, verbose_name="Nombre del receptor"),
        ),
        migrations.AddField(
            model_name="casointerno",
            name="receptor_sexo",
            field=models.CharField(
                blank=True,
                choices=[("M", "Mujer"), ("H", "Hombre")],
                max_length=1,
                verbose_name="Sexo del NNA (receptor)",
            ),
        ),
        migrations.AddField(
            model_name="casointerno",
            name="receptores_adicionales",
            field=models.JSONField(blank=True, default=list, verbose_name="Receptores adicionales"),
        ),
        migrations.AddField(
            model_name="historicalcasointerno",
            name="generador_iniciales",
            field=models.CharField(blank=True, max_length=50, verbose_name="Iniciales del NNA (generador)"),
        ),
        migrations.AddField(
            model_name="historicalcasointerno",
            name="generador_nombre",
            field=models.CharField(blank=True, max_length=255, verbose_name="Nombre del generador"),
        ),
        migrations.AddField(
            model_name="historicalcasointerno",
            name="generador_sexo",
            field=models.CharField(
                blank=True,
                choices=[("M", "Mujer"), ("H", "Hombre")],
                max_length=1,
                verbose_name="Sexo del NNA (generador)",
            ),
        ),
        migrations.AddField(
            model_name="historicalcasointerno",
            name="receptor_iniciales",
            field=models.CharField(blank=True, max_length=50, verbose_name="Iniciales del NNA (receptor)"),
        ),
        migrations.AddField(
            model_name="historicalcasointerno",
            name="receptor_nombre",
            field=models.CharField(blank=True, max_length=255, verbose_name="Nombre del receptor"),
        ),
        migrations.AddField(
            model_name="historicalcasointerno",
            name="receptor_sexo",
            field=models.CharField(
                blank=True,
                choices=[("M", "Mujer"), ("H", "Hombre")],
                max_length=1,
                verbose_name="Sexo del NNA (receptor)",
            ),
        ),
        migrations.AddField(
            model_name="historicalcasointerno",
            name="receptores_adicionales",
            field=models.JSONField(blank=True, default=list, verbose_name="Receptores adicionales"),
        ),
    ]
