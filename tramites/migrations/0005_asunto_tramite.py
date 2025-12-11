from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0004_relax_optional_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="casointerno",
            name="asunto",
            field=models.TextField(blank=True, verbose_name="Asunto"),
        ),
        migrations.AddField(
            model_name="historicalcasointerno",
            name="asunto",
            field=models.TextField(blank=True, verbose_name="Asunto"),
        ),
    ]
