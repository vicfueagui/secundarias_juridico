from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
import pandas as pd

BASE_DIR = Path(__file__).parent.resolve()

@dataclass
class Row:
    nombre_completo: str
    rfc: str
    filiacion: str
    cct: str
    no_licencia: str
    dias: int
    del_: str
    al: str

    @property
    def del(self) -> str:
        return self.del_

def build_rows() -> list[dict]:
    # EJEMPLO: aquí normalmente leerías de DB, Excel, CSV, etc.
    df = pd.DataFrame(
        [
            {
                "nombre_completo": "PÉREZ LÓPEZ, JUAN CARLOS",
                "rfc": "PEPJ800101XXX",
                "filiacion": "1234567890",
                "cct": "31ABC0001X",
                "no_licencia": "001",
                "dias": 14,
                "del": "01/01/2025",
                "al": "14/01/2025",
            },
            {
                "nombre_completo": "GÓMEZ MARTÍN, ANA",
                "rfc": "GOMA850505YYY",
                "filiacion": "0987654321",
                "cct": "31ABC0002Y",
                "no_licencia": "002",
                "dias": 7,
                "del": "05/01/2025",
                "al": "11/01/2025",
            },
        ]
    )

    # Si quieres ordenar, filtrar, agrupar, etc., hazlo aquí con Pandas.
    # df = df.sort_values(["nombre_completo"])

    return df.to_dict(orient="records")

def render_pdf(output_pdf: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(str(BASE_DIR / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("reporte.html")

    context = {
        "title": "Relación de licencias médicas",
        "header_image_path": "static/img/header.png",
        "periodo": "ENERO DEL 2025",
        "rows": build_rows(),
        "lugar": "Mérida",
        "estado": "Yucatán",
        "fecha_documento": "31 de octubre de 2025",
        "firmante_nombre": "LIC. MARIA ANTONIETA GARCIA GOMEZ",
        "firmante_cargo_linea1": "ENLACE DE ASESORES ESPECIALIZADOS DE",
        "firmante_cargo_linea2": "EDUCACIÓN SECUNDARIA",
        "cc_text": "C.c.p. Archivo.",
        "initials": "RIPN/magg/vmfa.",
        "footer_address": "Calle 124-C No. 319 entre 61 y 63 Fracc. Yucalpetén, C.P. 97238  —  Mérida, Yucatán, México (999) 930 39 50 Ext. 51411",
    }

    html = template.render(**context)

    # base_url es CLAVE: permite que WeasyPrint encuentre CSS e imágenes por rutas relativas
    HTML(string=html, base_url=str(BASE_DIR)).write_pdf(str(output_pdf))

if __name__ == "__main__":
    out = BASE_DIR / "salida.pdf"
    render_pdf(out)
    print(f"PDF generado: {out}")
