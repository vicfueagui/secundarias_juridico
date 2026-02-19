from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0022_minutas_adjuntas"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="casointerno",
            name="usuarios_involucrados",
            field=models.ManyToManyField(
                blank=True,
                related_name="casos_involucrados",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Usuarios involucrados",
            ),
        ),
    ]
