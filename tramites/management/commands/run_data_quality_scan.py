from __future__ import annotations

from django.core.management.base import BaseCommand

from tramites.services import data_quality


class Command(BaseCommand):
    help = "Ejecuta el servicio de calidad de datos y guarda un reporte auditable."

    def handle(self, *args, **options):
        run = data_quality.run_quality_scan(origen="cli")
        resumen = run.resumen or {}
        self.stdout.write(
            self.style.SUCCESS(
                "Corrida completada. Detectados={detected} Resueltos={resolved} Activos={active}".format(
                    detected=resumen.get("issues_detected", 0),
                    resolved=resumen.get("issues_resolved", 0),
                    active=resumen.get("issues_active_total", 0),
                )
            )
        )
