from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0019_expand_plantilla_telefono"),
    ]

    operations = [
        migrations.AddField(
            model_name="casointerno",
            name="minuta",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="tramites/minutas/casos/",
                validators=[django.core.validators.FileExtensionValidator(["pdf"])],
                verbose_name="Minuta (PDF)",
            ),
        ),
        migrations.AddField(
            model_name="historicalcasointerno",
            name="minuta",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="tramites/minutas/casos/",
                validators=[django.core.validators.FileExtensionValidator(["pdf"])],
                verbose_name="Minuta (PDF)",
            ),
        ),
        migrations.AddField(
            model_name="tramitecaso",
            name="minuta",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="tramites/minutas/tramites/",
                validators=[django.core.validators.FileExtensionValidator(["pdf"])],
                verbose_name="Minuta (PDF)",
            ),
        ),
        migrations.AddField(
            model_name="historicaltramitecaso",
            name="minuta",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="tramites/minutas/tramites/",
                validators=[django.core.validators.FileExtensionValidator(["pdf"])],
                verbose_name="Minuta (PDF)",
            ),
        ),
    ]
