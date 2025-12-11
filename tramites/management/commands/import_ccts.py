from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from tramites.services import protocolos_import


class Command(BaseCommand):
    help = "Importa o actualiza el catálogo de CCT de secundarias desde un archivo CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            required=True,
            help="Ruta al archivo CSV con los CCT (por ejemplo cct_secundarias.csv).",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["path"]).expanduser()
        if not csv_path.exists():
            raise CommandError(f"No se encontró el archivo CSV: {csv_path}")

        self.stdout.write(self.style.NOTICE(f"Importando catálogo de CCT desde {csv_path}..."))
        resultado = protocolos_import.importar_ccts(csv_path)
        self.stdout.write(
            self.style.SUCCESS(
                f"CCT creados: {resultado.ccts_creados}, actualizados: {resultado.ccts_actualizados}"
            )
        )
