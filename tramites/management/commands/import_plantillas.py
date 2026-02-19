from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from tramites.services import importar_plantillas


class Command(BaseCommand):
    help = "Importa o actualiza las plantillas de secundarias desde un archivo CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            required=True,
            help="Ruta al archivo CSV con las plantillas (por ejemplo REPORTE_PLANTILLA_2014_2025.csv).",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["path"]).expanduser()
        if not csv_path.exists():
            raise CommandError(f"No se encontró el archivo CSV: {csv_path}")

        self.stdout.write(self.style.NOTICE(f"Importando plantillas desde {csv_path}..."))
        resultado = importar_plantillas(csv_path)
        self.stdout.write(
            self.style.SUCCESS(
                "Centros creados: {centros_creados}, actualizados: {centros_actualizados}. "
                "Empleados creados: {empleados_creados}, actualizados: {empleados_actualizados}. "
                "Registros creados: {registros_creados}, actualizados: {registros_actualizados}. "
                "Claves creadas: {claves_creadas}, eliminadas: {claves_eliminadas}."
            ).format(
                centros_creados=resultado.centros_creados,
                centros_actualizados=resultado.centros_actualizados,
                empleados_creados=resultado.empleados_creados,
                empleados_actualizados=resultado.empleados_actualizados,
                registros_creados=resultado.registros_creados,
                registros_actualizados=resultado.registros_actualizados,
                claves_creadas=resultado.claves_creadas,
                claves_eliminadas=resultado.claves_eliminadas,
            )
        )
