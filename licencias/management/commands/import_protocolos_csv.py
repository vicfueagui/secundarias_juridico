"""Comando para importar la relación de protocolos desde CSV."""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from licencias.services import protocolos_import


class Command(BaseCommand):
    help = "Importa CCT y registros de la Relación de Protocolos desde archivos CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cct-path",
            required=True,
            help="Ruta al archivo CSV con el catálogo de CCT de secundarias.",
        )
        parser.add_argument(
            "--protocolos-path",
            required=True,
            help="Ruta al archivo CSV con el control histórico de protocolos.",
        )

    def handle(self, *args, **options):
        cct_path = Path(options["cct_path"]).expanduser()
        protocolos_path = Path(options["protocolos_path"]).expanduser()

        if not cct_path.exists():
            raise CommandError(f"El archivo de CCT no existe: {cct_path}")
        if not protocolos_path.exists():
            raise CommandError(f"El archivo de protocolos no existe: {protocolos_path}")

        self.stdout.write(self.style.NOTICE("Importando catálogo de CCT..."))
        resultado = protocolos_import.importar_desde_csv(
            archivo_ccts=cct_path,
            archivo_protocolos=protocolos_path,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"CCT creados: {resultado.ccts_creados}, actualizados: {resultado.ccts_actualizados}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Protocolos creados: {resultado.protocolos_creados}, actualizados: {resultado.protocolos_actualizados}"
            )
        )
        if resultado.errores:
            self.stdout.write(self.style.WARNING("Se detectaron incidencias:"))
            for error in resultado.errores:
                self.stdout.write(self.style.WARNING(f" - {error}"))
