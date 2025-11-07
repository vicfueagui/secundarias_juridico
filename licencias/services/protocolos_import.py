"""Servicios de importación para la relación de protocolos."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from django.db import transaction

from licencias import models
from licencias.utils import normalise_sistema


@dataclass
class ImportResult:
    ccts_creados: int = 0
    ccts_actualizados: int = 0
    protocolos_creados: int = 0
    protocolos_actualizados: int = 0
    errores: list[str] = None

    def __post_init__(self):
        if self.errores is None:
            self.errores = []


def _clean(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def _parse_fecha(valor: str | None) -> date | None:
    if not valor:
        return None
    valor = valor.strip()
    if not valor:
        return None
    formatos = ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y-%m-%d")
    for formato in formatos:
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    partes = valor.replace("-", "/").split("/")
    if len(partes) == 3:
        dia, mes, anno = partes
        if len(anno) == 3:
            anno = f"2{anno}"
        try:
            return date(int(anno), int(mes), int(dia))
        except ValueError:
            return None
    return None


def importar_ccts(archivo: Path, *, resultado: ImportResult | None = None) -> ImportResult:
    resultado = resultado or ImportResult()
    with archivo.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            data = {key.strip(): (value.strip() if value else "") for key, value in row.items()}
            cct_codigo = data.get("CCT") or data.get("cct")
            if not cct_codigo:
                continue
            defaults = {
                "nombre": data.get("c_nombre") or data.get("NOMBRE") or "",
                "asesor": data.get("ASESOR", ""),
                "servicio": data.get("tiponivelsub_c_servicion3", ""),
                "sostenimiento": normalise_sistema(data.get("sostenimiento_c_subcontrol", "")),
                "municipio": data.get("inmueble_c_nom_mun", ""),
                "turno": data.get("c_tuno_01", "") or data.get("Turno", ""),
            }
            obj, created = models.CCTSecundaria.objects.update_or_create(
                cct=cct_codigo.strip(), defaults=defaults
            )
            if created:
                resultado.ccts_creados += 1
            else:
                resultado.ccts_actualizados += 1
    return resultado


def importar_protocolos(
    archivo: Path,
    *,
    resultado: ImportResult | None = None,
) -> ImportResult:
    resultado = resultado or ImportResult()
    estatus_map = {
        "activo": models.RelacionProtocolo.Estatus.ACTIVO,
        "en seguimiento": models.RelacionProtocolo.Estatus.EN_SEGUIMIENTO,
        "seguimiento": models.RelacionProtocolo.Estatus.EN_SEGUIMIENTO,
        "cerrado": models.RelacionProtocolo.Estatus.CERRADO,
        "cancelado": models.RelacionProtocolo.Estatus.CANCELADO,
    }
    sexo_map = {
        "f": models.RelacionProtocolo.Sexo.MUJER,
        "femenino": models.RelacionProtocolo.Sexo.MUJER,
        "m": models.RelacionProtocolo.Sexo.HOMBRE,
        "masculino": models.RelacionProtocolo.Sexo.HOMBRE,
        "h": models.RelacionProtocolo.Sexo.HOMBRE,
        "hombre": models.RelacionProtocolo.Sexo.HOMBRE,
        "mujer": models.RelacionProtocolo.Sexo.MUJER,
        "x": models.RelacionProtocolo.Sexo.NO_ESPECIFICADO,
        "no especificado": models.RelacionProtocolo.Sexo.NO_ESPECIFICADO,
    }
    with archivo.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader, start=2):
            data = {key.strip(): (value.strip() if value else "") for key, value in row.items()}
            numero_raw = data.get("No.") or data.get("NO.") or data.get("ID")
            if not numero_raw:
                resultado.errores.append(f"Fila {idx}: sin ID.")
                continue
            try:
                numero = int(numero_raw)
            except ValueError:
                resultado.errores.append(f"Fila {idx}: ID inválido ({numero_raw}).")
                continue

            cct_codigo = data.get("CCT")
            if not cct_codigo:
                resultado.errores.append(f"Fila {idx}: sin CCT asociado.")
                continue
            try:
                cct_obj = models.CCTSecundaria.objects.get(cct=cct_codigo)
            except models.CCTSecundaria.DoesNotExist:
                resultado.errores.append(f"Fila {idx}: CCT {cct_codigo} no encontrado.")
                continue

            fecha = _parse_fecha(data.get("Fecha de inicio"))
            if not fecha:
                resultado.errores.append(
                    f"Fila {idx}: fecha de inicio inválida ({data.get('Fecha de inicio')})."
                )
                continue

            sexo_valor = sexo_map.get(data.get("SEXO", "").lower(), models.RelacionProtocolo.Sexo.NO_ESPECIFICADO)
            estatus_valor = estatus_map.get(
                data.get("Estatus", "").lower(), models.RelacionProtocolo.Estatus.ACTIVO
            )
            anio = data.get("AÑO") or data.get("AÑO.")
            if anio:
                try:
                    anio_valor = int(anio)
                except ValueError:
                    anio_valor = fecha.year
            else:
                anio_valor = fecha.year

            defaults = {
                "cct": cct_obj,
                "fecha_inicio": fecha,
                "iniciales": data.get("INICIALES") or "",
                "nombre_nna": data.get("Nombre del NNA") or "",
                "sexo": sexo_valor,
                "tipo_violencia": data.get("TIPO DE VIOLENCIA") or "",
                "descripcion": data.get("Descripción") or "",
                "asesor_juridico": data.get("NOMBRE ASESOR JURIDICO") or "",
                "estatus": estatus_valor,
                "comentarios": data.get("Comentarios") or "",
                "anio": anio_valor,
            }

            obj, created = models.RelacionProtocolo.objects.update_or_create(
                numero_registro=numero,
                defaults=defaults,
            )
            if created:
                resultado.protocolos_creados += 1
            else:
                resultado.protocolos_actualizados += 1
    return resultado


@transaction.atomic
def importar_desde_csv(
    *,
    archivo_ccts: Path,
    archivo_protocolos: Path,
) -> ImportResult:
    resultado = ImportResult()
    importar_ccts(archivo_ccts, resultado=resultado)
    importar_protocolos(archivo_protocolos, resultado=resultado)
    return resultado
