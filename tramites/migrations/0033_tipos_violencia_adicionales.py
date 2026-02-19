from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0032_remove_historicalcctsecundaria_history_user_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="casointerno",
            name="tipos_violencia_adicionales",
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name="Tipos de violencia adicionales",
            ),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="tipos_violencia_adicionales",
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name="Tipos de violencia adicionales",
            ),
        ),
    ]
