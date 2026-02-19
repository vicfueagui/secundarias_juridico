from __future__ import annotations

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from tramites import models


class Command(BaseCommand):
    help = "Restaura (o crea) un folio faltante como registro inactivo."

    def add_arguments(self, parser):
        parser.add_argument(
            "folio",
            type=str,
            help="Folio completo, ej: DES-AESP-INC/3/2026",
        )
        parser.add_argument(
            "--tipo",
            choices=["caso", "tramite"],
            default="caso",
            help="Tipo de folio (caso o tramite). Por defecto: caso.",
        )
        parser.add_argument(
            "--caso-id",
            type=int,
            default=None,
            help="ID del caso asociado (opcional).",
        )
        parser.add_argument(
            "--tramite-id",
            type=int,
            default=None,
            help="ID del trámite asociado (opcional).",
        )
        parser.add_argument(
            "--activo",
            action="store_true",
            help="Marca el folio como activo (por defecto queda inactivo).",
        )
        parser.add_argument(
            "--nota",
            type=str,
            default="Folio restaurado manualmente.",
            help="Nota a registrar en el folio.",
        )

    def handle(self, *args, **options):
        folio_text = options["folio"].strip()
        if not folio_text or "/" not in folio_text:
            raise CommandError("Formato de folio inválido.")

        parts = folio_text.split("/")
        if len(parts) < 3:
            raise CommandError("El folio debe incluir prefijo/numero/anio.")

        prefijo = "/".join(parts[:-2]).strip()
        numero_raw = parts[-2].strip()
        anio_raw = parts[-1].strip()

        if not numero_raw.isdigit() or not anio_raw.isdigit():
            raise CommandError("Número o año inválidos en el folio.")

        numero = int(numero_raw)
        anio = int(anio_raw)
        if anio < 2000 or anio > datetime.now().year + 1:
            raise CommandError("Año fuera de rango esperado.")

        caso = None
        tramite = None
        casos = []
        if options["caso_id"]:
            caso = models.CasoInterno.objects.filter(pk=options["caso_id"]).first()
            if not caso:
                raise CommandError("Caso no encontrado.")
            casos = [caso]
        if options["tramite_id"]:
            tramite = models.TramiteCaso.objects.filter(pk=options["tramite_id"]).first()
            if not tramite:
                raise CommandError("Trámite no encontrado.")

        registro, created = models.FolioRegistro.objects.get_or_create(
            folio=folio_text,
            defaults={
                "anio": anio,
                "prefijo": prefijo,
                "numero": numero,
                "tipo": options["tipo"],
                "tramite": tramite,
                "activo": options["activo"],
                "notas": options["nota"],
            },
        )

        if not created:
            registro.anio = anio
            registro.prefijo = prefijo
            registro.numero = numero
            registro.tipo = options["tipo"]
            registro.tramite = tramite
            registro.activo = options["activo"]
            if options["nota"]:
                registro.notas = options["nota"]
            registro.save()
        if casos:
            if registro.tramite_id:
                registro.tramite = None
                registro.save(update_fields=["tramite"])
            registro.casos.set(casos)
        elif tramite:
            registro.casos.clear()
        if casos:
            for caso in casos:
                if caso.numero_oficio != registro.folio:
                    caso.numero_oficio = registro.folio
                    caso.save(update_fields=["numero_oficio", "actualizado_en"])
        if tramite and tramite.numero_oficio != registro.folio:
            tramite.numero_oficio = registro.folio
            tramite.save(update_fields=["numero_oficio", "actualizado_en"])

        if not registro.activo:
            registro.eliminado_en = timezone.now()
            registro.save(update_fields=["eliminado_en"])

        models.FolioActividad.objects.create(
            folio=registro,
            accion="editado" if not created else "creado",
            usuario=None,
            detalle="Restauración manual de folio",
        )

        status = "creado" if created else "actualizado"
        self.stdout.write(self.style.SUCCESS(f"Folio {status}: {registro.folio}"))
