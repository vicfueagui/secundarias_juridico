from __future__ import annotations

from django.core.management.base import BaseCommand

from tramites.services import jobs


class Command(BaseCommand):
    help = "Encola jobs programados cuya fecha de ejecución ya venció."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100, help="Máximo de jobs programados a encolar.")

    def handle(self, *args, **options):
        limit = max(1, int(options.get("limit") or 100))
        created = jobs.schedule_due_jobs(limit=limit)
        self.stdout.write(self.style.SUCCESS(f"Jobs encolados: {len(created)}"))
