from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0004_controlinterno"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalcctsecundaria",
            name="id",
            field=models.CharField(
                blank=True,
                null=True,
                max_length=12,
                db_index=True,
                verbose_name="ID",
            ),
        ),
    ]
