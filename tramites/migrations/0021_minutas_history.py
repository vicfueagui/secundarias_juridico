from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("licencias", "0020_minutas_pdf"),
    ]

    # Estos campos ya se agregan en 0020_minutas_pdf.
    # Se mantiene el archivo para preservar la secuencia de migraciones.
    operations = []
