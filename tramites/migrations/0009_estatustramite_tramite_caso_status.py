from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0008_tramite_caso"),
    ]

    operations = [
        migrations.CreateModel(
            name="EstatusTramite",
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
                ("nombre", models.CharField(max_length=255, unique=True)),
                ("descripcion", models.TextField(blank=True)),
                ("esta_activo", models.BooleanField(default=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("orden", models.PositiveIntegerField(default=1)),
            ],
            options={
                "verbose_name": "Estatus de trámite",
                "verbose_name_plural": "Estatus de trámite",
                "ordering": ("orden", "nombre"),
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="HistoricalEstatusTramite",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("nombre", models.CharField(db_index=True, max_length=255)),
                ("descripcion", models.TextField(blank=True)),
                ("esta_activo", models.BooleanField(default=True)),
                ("creado_en", models.DateTimeField(blank=True, editable=False)),
                ("actualizado_en", models.DateTimeField(blank=True, editable=False)),
                ("orden", models.PositiveIntegerField(default=1)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Estatus de trámite",
                "verbose_name_plural": "historical Estatus de trámite",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AlterField(
            model_name="tramitecaso",
            name="estatus",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tramites_caso",
                to="licencias.estatustramite",
                verbose_name="Estatus del trámite",
            ),
        ),
        migrations.AlterField(
            model_name="historicaltramitecaso",
            name="estatus",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="licencias.estatustramite",
                verbose_name="Estatus del trámite",
            ),
        ),
    ]
