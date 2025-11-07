"""Servicio para importar licencias desde CSV."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from io import BytesIO, StringIO
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from dateutil import parser
from django.contrib.auth import get_user_model
from django.db import transaction

from licencias import models
from licencias.services import validators

User = get_user_model()


COLUMN_MAP = {
    "Persona que trabaja el trámite": "persona_tramita",
    "Licencia o trámite": "tipo_tramite",
    "Federal/ Estatal": "subsistema",
    "Trámite Inicial o prórroga": "tramite_inicial_o_prorroga",
    "Nombre del trabajador": "trabajador_nombre",
    "DIAGNOSTICO": "diagnostico",
    "Nombre del sindicato": "sindicato",
    "Contacto del trabajador y/o sindicato": "contacto",
    "Número de oficio del sindicato o escrito de origen": "oficio_origen_num",
    "Fecha de recepción del oficio del sindicato o escrito del trabajador en el nivel educativo": "fecha_recepcion_nivel",
    "Incidencias para la Integración del expediente/ prevención/ o contestación negativa del trámite": "incidencias_integracion",
    "Oficio de envío a la Subsecretaría / PRÓRROGAS de licencias": "oficio_envio_subsecretaria",
    "Fecha de recepción en la Subsecretaría /PRÓRROGAS de licencias": "fecha_recepcion_subsecretaria",
    "Incidencias para el visto bueno de la Subsecretaría": "incidencias_vobo",
    "Número de oficio y fecha de Visto Bueno de la Subsecretaría": "vobo_num_y_fecha",
    "Oficio de envío a Recursos Humanos de la Secretaría de Administración y Finanzas del Gobierno del Estado": "oficio_envio_rh",
    "Fecha de recepción del área de Recursos Humanos": "fecha_recepcion_rh",
    "Número de oficio y fecha de la resolución emitida por Recursos Humanos de la Secretaría de Administración y Finanzas del Gobierno del Estado": "oficio_resolucion_num_y_fecha",
    "RESULTADO DE LA RESOLUCIÓN EMITIDA POR RECURSOS HUMANOS": "resultado_resolucion",
    "Número de oficio y fecha de notificacíon al sindicato sobre la resolución.": "notif_sindicato",
    "Número de oficio y fecha de la notificación al trabajador sobre la resolución.": "notif_trabajador",
    "Fecha en la se realizó la notificacion al sindicato": "fecha_notif_sindicato",
    "Fecha en la se realizó la notificación al trabajador": "fecha_notif_trabajador",
}

NOTIFICACION_COLUMNAS = [
    ("notif_sindicato", models.Notificacion.Destinatario.SINDICATO),
    ("notif_trabajador", models.Notificacion.Destinatario.TRABAJADOR),
]


@dataclass
class FilaResultado:
    indice: int
    datos: Dict[str, Any]
    errores: List[str] = field(default_factory=list)
    tramite: Optional[models.Tramite] = None


def _parse_fecha(valor: Any) -> Optional[date]:
    if pd.isna(valor) or valor in {"", None}:
        return None
    if isinstance(valor, date):
        return valor
    try:
        return parser.parse(str(valor), dayfirst=True).date()
    except (ValueError, TypeError, OverflowError):
        return None


def _normalizar_tramite_inicial(valor: Any) -> str:
    valor = str(valor).strip().lower()
    if not valor:
        return models.Tramite.TipoSolicitud.DESCONOCIDO
    if "inicial" in valor:
        return models.Tramite.TipoSolicitud.INICIAL
    if "prórroga" in valor or "prorroga" in valor:
        return models.Tramite.TipoSolicitud.PRORROGA
    return models.Tramite.TipoSolicitud.DESCONOCIDO


def _obtener_catalogo(modelo, valor: Any, crear: bool, errores: List[str]):
    if pd.isna(valor) or not str(valor).strip():
        return None
    nombre = str(valor).strip()
    try:
        return modelo.objects.get(nombre__iexact=nombre)
    except modelo.DoesNotExist:
        if not crear:
            errores.append(f"Valor '{nombre}' no existe en {modelo.__name__}.")
            return None
        return modelo.objects.create(nombre=nombre)


def _resolver_etapa_inicial() -> models.Etapa:
    etapa = models.Etapa.objects.filter(nombre__icontains="ingreso").first()
    if not etapa:
        etapa = models.Etapa.objects.order_by("orden").first()
    if not etapa:
        etapa = models.Etapa.objects.create(nombre="Ingreso", orden=1)
    return etapa


def _registrar_notificaciones(tramite: models.Tramite, fila: Dict[str, Any]) -> None:
    for columna, destinatario in NOTIFICACION_COLUMNAS:
        texto = fila.get(columna)
        fecha_col = (
            "fecha_notif_sindicato"
            if destinatario == models.Notificacion.Destinatario.SINDICATO
            else "fecha_notif_trabajador"
        )
        fecha_valor = _parse_fecha(fila.get(fecha_col))
        if texto or fecha_valor:
            models.Notificacion.objects.create(
                tramite=tramite,
                destinatario=destinatario,
                numero_oficio=str(texto or "").strip(),
                fecha=fecha_valor,
            )


@dataclass
class ResultadoImportacion:
    cargados: List[FilaResultado] = field(default_factory=list)
    errores: List[FilaResultado] = field(default_factory=list)

    @property
    def resumen(self) -> Dict[str, Any]:
        return {
            "total": len(self.cargados) + len(self.errores),
            "cargados": len(self.cargados),
            "errores": len(self.errores),
        }


def _preparar_dataframe(archivo) -> pd.DataFrame:
    if hasattr(archivo, "read"):
        contenido = archivo.read()
        archivo.seek(0)
        if isinstance(contenido, bytes):
            archivo_io = BytesIO(contenido)
        else:
            archivo_io = StringIO(contenido)
        df = pd.read_csv(archivo_io, header=1, encoding="utf-8")
    else:
        df = pd.read_csv(archivo, header=1, encoding="utf-8")
    return df.fillna("")


def procesar_archivo(archivo, crear_catalogos: bool = True, usuario: Optional[User] = None) -> Dict[str, Any]:
    """Procesa un archivo cargado desde el formulario."""
    resultado = cargar_desde_dataframe(
        _preparar_dataframe(archivo), crear_catalogos=crear_catalogos, usuario=usuario
    )
    return {
        "resumen": resultado.resumen,
        "errores": resultado.errores,
        "cargados": resultado.cargados,
    }


def cargar_desde_csv(path: str, *, crear_catalogos: bool = True, usuario: Optional[User] = None) -> ResultadoImportacion:
    df = pd.read_csv(path, header=1, encoding="utf-8").fillna("")
    return cargar_desde_dataframe(df, crear_catalogos=crear_catalogos, usuario=usuario)


def cargar_desde_dataframe(
    df: pd.DataFrame, *, crear_catalogos: bool = True, usuario: Optional[User] = None
) -> ResultadoImportacion:
    resultado = ResultadoImportacion()
    etapa_inicial = _resolver_etapa_inicial()
    for idx, row in df.iterrows():
        fila = FilaResultado(indice=idx + 2, datos=row.to_dict())
        try:
            tramite = _crear_tramite_desde_fila(
                fila.datos, etapa_inicial, crear_catalogos, usuario, fila.errores
            )
            if fila.errores:
                raise ValueError("Errores de validación.")
            fila.tramite = tramite
            resultado.cargados.append(fila)
        except Exception as exc:  # noqa: BLE001
            fila.errores.append(str(exc))
            resultado.errores.append(fila)
    return resultado


def _crear_tramite_desde_fila(
    fila: Dict[str, Any],
    etapa_inicial: models.Etapa,
    crear_catalogos: bool,
    usuario: Optional[User],
    errores: List[str],
) -> models.Tramite:
    datos = {}
    for columna, campo in COLUMN_MAP.items():
        datos[campo] = fila.get(columna, "")

    tipo_tramite = _obtener_catalogo(models.TipoTramite, datos["tipo_tramite"], crear_catalogos, errores)
    subsistema = _obtener_catalogo(models.Subsistema, datos["subsistema"], crear_catalogos, errores)
    diagnostico = _obtener_catalogo(models.Diagnostico, datos.get("diagnostico"), crear_catalogos, errores)
    sindicato = _obtener_catalogo(models.Sindicato, datos.get("sindicato"), crear_catalogos, errores)
    resultado_resolucion = _obtener_catalogo(models.Resultado, datos.get("resultado_resolucion"), crear_catalogos, errores)

    tramite = models.Tramite(
        tipo_tramite=tipo_tramite,
        subsistema=subsistema,
        tramite_inicial_o_prorroga=_normalizar_tramite_inicial(datos.get("tramite_inicial_o_prorroga")),
        trabajador_nombre=str(datos.get("trabajador_nombre", "")).strip(),
        diagnostico=diagnostico,
        sindicato=sindicato,
        contacto=str(datos.get("contacto", "")).strip(),
        oficio_origen_num=str(datos.get("oficio_origen_num", "")).strip(),
        fecha_recepcion_nivel=_parse_fecha(datos.get("fecha_recepcion_nivel")),
        incidencias_integracion=str(datos.get("incidencias_integracion", "")).strip(),
        oficio_envio_subsecretaria=str(datos.get("oficio_envio_subsecretaria", "")).strip(),
        fecha_recepcion_subsecretaria=_parse_fecha(datos.get("fecha_recepcion_subsecretaria")),
        incidencias_vobo=str(datos.get("incidencias_vobo", "")).strip(),
        vobo_num_y_fecha=str(datos.get("vobo_num_y_fecha", "")).strip(),
        oficio_envio_rh=str(datos.get("oficio_envio_rh", "")).strip(),
        fecha_recepcion_rh=_parse_fecha(datos.get("fecha_recepcion_rh")),
        oficio_resolucion_num_y_fecha=str(datos.get("oficio_resolucion_num_y_fecha", "")).strip(),
        resultado_resolucion=resultado_resolucion,
        persona_tramita=str(datos.get("persona_tramita", "")).strip(),
        estado_actual=etapa_inicial,
        user_responsable=usuario,
    )

    try:
        validators.validar_fechas_chronologicas(tramite)
        validators.validar_campos_por_etapa(tramite)
    except Exception as exc:  # noqa: BLE001
        errores.append(str(exc))

    if not tramite.trabajador_nombre:
        errores.append("Nombre del trabajador es obligatorio.")
    if not tipo_tramite:
        errores.append("Tipo de trámite es obligatorio.")
    if not subsistema:
        errores.append("Subsistema es obligatorio.")

    if errores:
        raise ValueError(", ".join(errores))

    with transaction.atomic():
        tramite.save()
        _registrar_notificaciones(tramite, datos)
    return tramite
