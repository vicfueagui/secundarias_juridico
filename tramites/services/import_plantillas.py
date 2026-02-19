from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from django.db import transaction

from tramites import models


@dataclass
class ImportPlantillaResult:
    centros_creados: int = 0
    centros_actualizados: int = 0
    empleados_creados: int = 0
    empleados_actualizados: int = 0
    registros_creados: int = 0
    registros_actualizados: int = 0
    claves_creadas: int = 0
    claves_eliminadas: int = 0


def _iter_rows(csv_path: Path) -> Iterable[dict]:
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield row


def _clean_value(value: Optional[str]) -> str:
    return (value or "").strip()


def _parse_int(value: Optional[str]) -> Optional[int]:
    value = _clean_value(value)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _clean_phone(value: Optional[str]) -> str:
    cleaned = _clean_value(value)
    if cleaned and set(cleaned) == {"#"}:
        return ""
    return cleaned


def _split_claves(raw_value: Optional[str]) -> list[str]:
    raw = _clean_value(raw_value)
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def importar_plantillas(csv_path: Path) -> ImportPlantillaResult:
    resultado = ImportPlantillaResult()

    with transaction.atomic():
        for row in _iter_rows(csv_path):
            origen_id = _parse_int(row.get("ID"))
            if not origen_id:
                continue

            cct = _clean_value(row.get("CCT"))
            if not cct:
                continue

            centro_defaults = {
                "nombre": _clean_value(row.get("CT")),
                "municipio": _clean_value(row.get("MUNICIPIO")),
                "asesor": _clean_value(row.get("ASESOR")),
                "sostenimiento": _clean_value(row.get("SOSTENIMIENTO")),
                "subnivel": _clean_value(row.get("SUBNIVEL")),
                "turno": _clean_value(row.get("TURNO")),
            }
            centro_obj, centro_created = models.PlantillaCentroTrabajo.objects.update_or_create(
                cct=cct,
                defaults=centro_defaults,
            )
            if centro_created:
                resultado.centros_creados += 1
            else:
                resultado.centros_actualizados += 1

            rfc = _clean_value(row.get("RFC")) or None
            curp = _clean_value(row.get("CURP")) or None
            empleado_defaults = {
                "nombre": _clean_value(row.get("NOMBRE")),
                "rfc": rfc,
                "curp": curp,
                "correo": _clean_value(row.get("CORREO")),
                "telefono": _clean_phone(row.get("TELEFONO")),
                "celular": _clean_phone(row.get("CELULAR")),
                "direccion": _clean_value(row.get("DIRECCION")),
                "colonia": _clean_value(row.get("COLONIA")),
                "codigo_postal": _clean_value(row.get("CODIGO_POSTAL")),
            }
            empleado_obj = None
            if rfc:
                empleado_obj = models.PlantillaEmpleado.objects.filter(rfc=rfc).first()
            if not empleado_obj and curp:
                empleado_obj = models.PlantillaEmpleado.objects.filter(curp=curp).first()

            if empleado_obj:
                for campo, valor in empleado_defaults.items():
                    setattr(empleado_obj, campo, valor)
                empleado_obj.save()
                empleado_created = False
            else:
                empleado_obj = models.PlantillaEmpleado.objects.create(**empleado_defaults)
                empleado_created = True

            if empleado_created:
                resultado.empleados_creados += 1
            else:
                resultado.empleados_actualizados += 1

            registro_defaults = {
                "centro_trabajo": centro_obj,
                "empleado": empleado_obj,
                "situacion": _clean_value(row.get("SITUACION")),
                "funcion": _clean_value(row.get("FUNCION")),
                "grado_grupo_horas": _clean_value(row.get("GRADO_GRUPO_HORAS")),
                "ciclo": _clean_value(row.get("CICLO")),
                "anio": _parse_int(row.get("ANO")),
            }
            registro_obj, registro_created = models.PlantillaRegistro.objects.update_or_create(
                origen_id=origen_id,
                defaults=registro_defaults,
            )
            if registro_created:
                resultado.registros_creados += 1
            else:
                resultado.registros_actualizados += 1

            claves = set(_split_claves(row.get("CLAVE_PRESUPESTAL")))
            existentes = set(registro_obj.claves.values_list("clave", flat=True))

            eliminar = existentes - claves
            if eliminar:
                borrados, _ = registro_obj.claves.filter(clave__in=eliminar).delete()
                resultado.claves_eliminadas += borrados

            agregar = claves - existentes
            if agregar:
                nuevos = [
                    models.PlantillaClavePresupuestal(registro=registro_obj, clave=clave)
                    for clave in sorted(agregar)
                ]
                models.PlantillaClavePresupuestal.objects.bulk_create(nuevos)
                resultado.claves_creadas += len(nuevos)

    return resultado
