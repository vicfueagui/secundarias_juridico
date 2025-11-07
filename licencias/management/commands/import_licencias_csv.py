"""Comando para importar licencias desde CSV."""
from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from licencias.services import import_csv

User = get_user_model()


class Command(BaseCommand):
    help = "Importa licencias de Secundaria desde un archivo CSV normalizado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            required=True,
            help="Ruta absoluta al archivo CSV.",
        )
        parser.add_argument(
            "--username",
            help="Usuario responsable a asociar al proceso.",
        )
        parser.add_argument(
            "--create-missing-catalogs",
            action="store_true",
            default=False,
            help="Crear registros de catálogos inexistentes.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"El archivo {path} no existe.")

        usuario = None
        username = options.get("username")
        if username:
            try:
                usuario = User.objects.get(username=username)
            except User.DoesNotExist as exc:
                raise CommandError(f"Usuario {username} no encontrado.") from exc

        self.stdout.write(self.style.NOTICE(f"Importando archivo {path} ..."))
        resultado = import_csv.cargar_desde_csv(
            str(path),
            crear_catalogos=options["create_missing_catalogs"],
            usuario=usuario,
        )
        resumen = resultado.resumen

        self.stdout.write(self.style.SUCCESS(f"Filas cargadas: {resumen['cargados']}"))
        self.stdout.write(self.style.WARNING(f"Filas con error: {resumen['errores']}"))

        if resultado.errores:
            self.stdout.write(self.style.ERROR("Detalle de errores:"))
            for fila in resultado.errores:
                self.stdout.write(
                    f"Fila {fila.indice}: {', '.join(fila.errores)}"
                )

