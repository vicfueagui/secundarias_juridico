from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from tramites import models
from tramites.utils import normalise_sistema


@dataclass
class ImportCCTResult:
    ccts_creados: int = 0
    ccts_actualizados: int = 0


def _iter_rows(csv_path: Path) -> Iterable[dict]:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield row


def importar_ccts(csv_path: Path) -> ImportCCTResult:
    resultado = ImportCCTResult()
    for row in _iter_rows(csv_path):
        cct = (row.get("CCT") or "").strip()
        if not cct:
            continue
        nombre = (row.get("c_nombre") or "").strip()
        asesor = (row.get("ASESOR") or "").strip()
        sostenimiento = normalise_sistema(row.get("sostenimiento_c_subcontrol") or "")
        servicio = (row.get("tiponivelsub_c_servicion3") or "").strip()

        obj, created = models.CCTSecundaria.objects.update_or_create(
            cct=cct,
            defaults={
                "nombre": nombre,
                "asesor": asesor,
                "sostenimiento": sostenimiento,
                "servicio": servicio,
            },
        )
        if created:
            resultado.ccts_creados += 1
        else:
            resultado.ccts_actualizados += 1
    return resultado
