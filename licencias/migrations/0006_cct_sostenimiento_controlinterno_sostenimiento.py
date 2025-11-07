from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0005_alter_historicalcctsecundaria_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="cctsecundaria",
            name="sostenimiento",
            field=models.CharField(
                blank=True,
                help_text="Indica si el centro es federal o estatal.",
                max_length=255,
                verbose_name="Tipo de sostenimiento (sostenimiento_c_subcontrol)",
            ),
        ),
        migrations.AddField(
            model_name="historicalcctsecundaria",
            name="sostenimiento",
            field=models.CharField(
                blank=True,
                help_text="Indica si el centro es federal o estatal.",
                max_length=255,
                verbose_name="Tipo de sostenimiento (sostenimiento_c_subcontrol)",
            ),
        ),
        migrations.AddField(
            model_name="controlinterno",
            name="sostenimiento_c_subcontrol",
            field=models.CharField(
                blank=True,
                help_text="Tipo de sistema del centro de trabajo.",
                max_length=255,
                verbose_name="Sostenimiento (sostenimiento_c_subcontrol)",
            ),
        ),
        migrations.AddField(
            model_name="historicalcontrolinterno",
            name="sostenimiento_c_subcontrol",
            field=models.CharField(
                blank=True,
                help_text="Tipo de sistema del centro de trabajo.",
                max_length=255,
                verbose_name="Sostenimiento (sostenimiento_c_subcontrol)",
            ),
        ),
    ]
