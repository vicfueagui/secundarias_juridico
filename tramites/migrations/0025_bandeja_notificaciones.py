from __future__ import annotations

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("licencias", "0024_merge_0020_licencias_0023_caso_usuarios_involucrados"),
    ]

    operations = [
        migrations.CreateModel(
            name="BandejaNotificacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("evento", models.CharField(choices=[("caso_creado", "Caso creado"), ("caso_actualizado", "Caso actualizado"), ("caso_estatus", "Estatus de caso actualizado"), ("caso_eliminado", "Caso eliminado"), ("tramite_creado", "Trámite asociado creado"), ("tramite_actualizado", "Trámite asociado actualizado"), ("tramite_estatus", "Estatus de trámite actualizado"), ("tramite_eliminado", "Trámite asociado eliminado"), ("registro_leido", "Registro leído")], max_length=40)),
                ("titulo", models.CharField(max_length=255)),
                ("mensaje", models.TextField(blank=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("referencia", models.CharField(blank=True, help_text="Texto de referencia cuando el registro ya no existe.", max_length=255, verbose_name="Referencia")),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="notificaciones_emitidas", to=settings.AUTH_USER_MODEL, verbose_name="Generado por")),
                ("caso", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="notificaciones", to="licencias.casointerno", verbose_name="Caso")),
                ("tramite", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="notificaciones", to="licencias.tramitecaso", verbose_name="Trámite asociado")),
            ],
            options={
                "verbose_name": "Notificación (bandeja)",
                "verbose_name_plural": "Notificaciones (bandeja)",
                "ordering": ("-creado_en",),
            },
        ),
        migrations.CreateModel(
            name="BandejaNotificacionDestinatario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("leido", models.BooleanField(default=False)),
                ("leido_en", models.DateTimeField(blank=True, null=True)),
                ("notificacion", models.ForeignKey(on_delete=models.CASCADE, related_name="destinatarios", to="licencias.bandejanotificacion", verbose_name="Notificación")),
                ("usuario", models.ForeignKey(on_delete=models.CASCADE, related_name="notificaciones_recibidas", to=settings.AUTH_USER_MODEL, verbose_name="Usuario")),
            ],
            options={
                "verbose_name": "Destinatario de notificación",
                "verbose_name_plural": "Destinatarios de notificaciones",
                "unique_together": {("notificacion", "usuario")},
            },
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="usuarios_involucrados",
            field=models.ManyToManyField(blank=True, related_name="tramites_involucrados", to=settings.AUTH_USER_MODEL, verbose_name="Usuarios involucrados"),
        ),
    ]
