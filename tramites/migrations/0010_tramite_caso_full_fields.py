from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0009_estatustramite_tramite_caso_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="tramitecaso",
            name="dirigido_a",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tramites_caso",
                to="licencias.destinatario",
                verbose_name="Dirigido a",
            ),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="generador_iniciales",
            field=models.CharField(blank=True, max_length=50, verbose_name="Iniciales del NNA (generador)"),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="generador_nombre",
            field=models.CharField(blank=True, max_length=255, verbose_name="Nombre del generador"),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="generador_sexo",
            field=models.CharField(
                blank=True,
                choices=[("M", "Mujer"), ("H", "Hombre")],
                max_length=1,
                verbose_name="Sexo del NNA (generador)",
            ),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="receptor_iniciales",
            field=models.CharField(blank=True, max_length=50, verbose_name="Iniciales del NNA (receptor)"),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="receptor_nombre",
            field=models.CharField(blank=True, max_length=255, verbose_name="Nombre del receptor"),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="receptor_sexo",
            field=models.CharField(
                blank=True,
                choices=[("M", "Mujer"), ("H", "Hombre")],
                max_length=1,
                verbose_name="Sexo del NNA (receptor)",
            ),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="receptores_adicionales",
            field=models.JSONField(blank=True, default=list, verbose_name="Receptores adicionales"),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="solicitante",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tramites_caso",
                to="licencias.solicitante",
                verbose_name="Solicitante",
            ),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="tipo_violencia",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tramites_caso",
                to="licencias.tipoviolencia",
                verbose_name="Tipo de violencia",
            ),
        ),
        migrations.AddField(
            model_name="historicaltramitecaso",
            name="dirigido_a",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="licencias.destinatario",
                verbose_name="Dirigido a",
            ),
        ),
        migrations.AddField(
            model_name="historicaltramitecaso",
            name="generador_iniciales",
            field=models.CharField(blank=True, max_length=50, verbose_name="Iniciales del NNA (generador)"),
        ),
        migrations.AddField(
            model_name="historicaltramitecaso",
            name="generador_nombre",
            field=models.CharField(blank=True, max_length=255, verbose_name="Nombre del generador"),
        ),
        migrations.AddField(
            model_name="historicaltramitecaso",
            name="generador_sexo",
            field=models.CharField(
                blank=True,
                choices=[("M", "Mujer"), ("H", "Hombre")],
                max_length=1,
                verbose_name="Sexo del NNA (generador)",
            ),
        ),
        migrations.AddField(
            model_name="historicaltramitecaso",
            name="receptor_iniciales",
            field=models.CharField(blank=True, max_length=50, verbose_name="Iniciales del NNA (receptor)"),
        ),
        migrations.AddField(
            model_name="historicaltramitecaso",
            name="receptor_nombre",
            field=models.CharField(blank=True, max_length=255, verbose_name="Nombre del receptor"),
        ),
        migrations.AddField(
            model_name="historicaltramitecaso",
            name="receptor_sexo",
            field=models.CharField(
                blank=True,
                choices=[("M", "Mujer"), ("H", "Hombre")],
                max_length=1,
                verbose_name="Sexo del NNA (receptor)",
            ),
        ),
        migrations.AddField(
            model_name="historicaltramitecaso",
            name="receptores_adicionales",
            field=models.JSONField(blank=True, default=list, verbose_name="Receptores adicionales"),
        ),
        migrations.AddField(
            model_name="historicaltramitecaso",
            name="solicitante",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="licencias.solicitante",
                verbose_name="Solicitante",
            ),
        ),
        migrations.AddField(
            model_name="historicaltramitecaso",
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
