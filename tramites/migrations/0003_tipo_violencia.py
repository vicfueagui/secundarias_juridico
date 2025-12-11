from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0002_prefijo_oficio"),
    ]

    operations = [
        migrations.CreateModel(
            name="TipoViolencia",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("nombre", models.CharField(max_length=255, unique=True)),
                ("descripcion", models.TextField(blank=True)),
                ("esta_activo", models.BooleanField(default=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Tipo de violencia",
                "verbose_name_plural": "Tipos de violencia",
                "ordering": ("nombre",),
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="HistoricalTipoViolencia",
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
                "verbose_name": "historical Tipo de violencia",
                "verbose_name_plural": "historical Tipos de violencia",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AddField(
            model_name="casointerno",
            name="tipo_violencia",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="casos",
                to="licencias.tipoviolencia",
                verbose_name="Tipo de violencia",
            ),
        ),
        migrations.AddField(
            model_name="historicalcasointerno",
            name="tipo_violencia",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="licencias.tipoviolencia",
                verbose_name="Tipo de violencia",
            ),
        ),
    ]
