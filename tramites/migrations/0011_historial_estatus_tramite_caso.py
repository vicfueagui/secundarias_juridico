from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0010_tramite_caso_full_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HistorialEstatusTramiteCaso",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "fecha_cambio",
                    models.DateTimeField(auto_now_add=True, verbose_name="Fecha de cambio"),
                ),
                ("comentario", models.TextField(blank=True, verbose_name="Comentario")),
                (
                    "estatus_anterior",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="licencias.estatustramite",
                        verbose_name="Estatus anterior",
                    ),
                ),
                (
                    "estatus_nuevo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="licencias.estatustramite",
                        verbose_name="Estatus nuevo",
                    ),
                ),
                (
                    "tramite",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="historial_estatus",
                        to="licencias.tramitecaso",
                        verbose_name="Trámite del caso",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="cambios_estatus_tramites",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Registrado por",
                    ),
                ),
            ],
            options={
                "ordering": ("-fecha_cambio",),
                "verbose_name": "Historial de estatus de trámite asociado",
                "verbose_name_plural": "Historial de estatus de trámites asociados",
            },
        ),
    ]
