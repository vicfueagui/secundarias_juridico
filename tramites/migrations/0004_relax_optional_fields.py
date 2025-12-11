from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0003_tipo_violencia"),
    ]

    operations = [
        migrations.AlterField(
            model_name="casointerno",
            name="area_origen_inicial",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="casos_origen",
                to="licencias.areaproceso",
                verbose_name="Área de origen",
            ),
        ),
        migrations.AlterField(
            model_name="casointerno",
            name="descripcion_breve",
            field=models.CharField(
                blank=True, max_length=255, verbose_name="Descripción breve"
            ),
        ),
        migrations.AlterField(
            model_name="historicalcasointerno",
            name="area_origen_inicial",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="licencias.areaproceso",
                verbose_name="Área de origen",
            ),
        ),
        migrations.AlterField(
            model_name="historicalcasointerno",
            name="descripcion_breve",
            field=models.CharField(
                blank=True, max_length=255, verbose_name="Descripción breve"
            ),
        ),
    ]
