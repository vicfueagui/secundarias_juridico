from __future__ import annotations

from django.core.management.base import BaseCommand

from tramites.services import jobs


class Command(BaseCommand):
    help = "Procesa jobs asíncronos pendientes."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20, help="Cantidad máxima de jobs a procesar.")
        parser.add_argument(
            "--worker-name",
            default="cli-worker",
            help="Nombre identificador del worker para trazabilidad.",
        )

    def handle(self, *args, **options):
        limit = max(1, int(options.get("limit") or 20))
        worker_name = (options.get("worker_name") or "cli-worker").strip() or "cli-worker"
        processed = jobs.run_pending_jobs(limit=limit, worker_name=worker_name)
        self.stdout.write(self.style.SUCCESS(f"Jobs procesados: {len(processed)}"))
