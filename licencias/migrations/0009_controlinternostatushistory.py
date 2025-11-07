from __future__ import annotations

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0008_controlinterno_status_defaults"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ControlInternoStatusHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("estatus_anterior", models.CharField(blank=True, max_length=150, verbose_name="Estatus anterior")),
                ("estatus_nuevo", models.CharField(max_length=150, verbose_name="Estatus nuevo")),
                ("cambiado_en", models.DateTimeField(auto_now_add=True, verbose_name="Fecha de cambio")),
                (
                    "cambiado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Registrado por",
                    ),
                ),
                (
                    "control",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="estatus_historial",
                        to="licencias.controlinterno",
                        verbose_name="Control interno",
                    ),
                ),
            ],
            options={
                "verbose_name": "Historial de estatus",
                "verbose_name_plural": "Historial de estatus",
                "ordering": ("-cambiado_en",),
            },
        ),
    ]
