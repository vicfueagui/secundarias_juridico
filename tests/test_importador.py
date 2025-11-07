from __future__ import annotations

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase

from licencias import models
from licencias.services import import_csv

User = get_user_model()


class ImportadorCSVTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.subsistema = models.Subsistema.objects.create(nombre="Federal")
        cls.tipo_tramite = models.TipoTramite.objects.create(nombre="Licencia 754")
        cls.resultado = models.Resultado.objects.create(nombre="Procedente")
        cls.etapa = models.Etapa.objects.create(nombre="Ingreso", orden=1)

    def test_importa_fila_valida(self):
        datos = {
            "Persona que trabaja el trámite": ["Ana"],
            "Licencia o trámite": [self.tipo_tramite.nombre],
            "Federal/ Estatal": [self.subsistema.nombre],
            "Trámite Inicial o prórroga": ["Trámite inicial"],
            "Nombre del trabajador": ["Juan Pérez"],
            "DIAGNOSTICO": [""],
            "Nombre del sindicato": [""],
            "Contacto del trabajador y/o sindicato": [""],
            "Número de oficio del sindicato o escrito de origen": ["OF-123"],
            "Fecha de recepción del oficio del sindicato o escrito del trabajador en el nivel educativo": ["2024-01-10"],
            "Incidencias para la Integración del expediente/ prevención/ o contestación negativa del trámite": [""],
            "Oficio de envío a la Subsecretaría / PRÓRROGAS de licencias": [""],
            "Fecha de recepción en la Subsecretaría /PRÓRROGAS de licencias": [""],
            "Incidencias para el visto bueno de la Subsecretaría": [""],
            "Número de oficio y fecha de Visto Bueno de la Subsecretaría": [""],
            "Oficio de envío a Recursos Humanos de la Secretaría de Administración y Finanzas del Gobierno del Estado": [""],
            "Fecha de recepción del área de Recursos Humanos": [""],
            "Número de oficio y fecha de la resolución emitida por Recursos Humanos de la Secretaría de Administración y Finanzas del Gobierno del Estado": [""],
            "RESULTADO DE LA RESOLUCIÓN EMITIDA POR RECURSOS HUMANOS": [self.resultado.nombre],
            "Número de oficio y fecha de notificacíon al sindicato sobre la resolución.": [""],
            "Número de oficio y fecha de la notificación al trabajador sobre la resolución.": [""],
            "Fecha en la se realizó la notificacion al sindicato": [""],
            "Fecha en la se realizó la notificación al trabajador": [""],
        }
        df = pd.DataFrame(datos)
        resultado = import_csv.cargar_desde_dataframe(df, crear_catalogos=False)
        self.assertEqual(resultado.resumen["cargados"], 1)
        self.assertEqual(models.Tramite.objects.count(), 1)

    def test_reporta_error_si_falta_tipo_tramite(self):
        datos = {
            "Persona que trabaja el trámite": ["Ana"],
            "Licencia o trámite": [""],
            "Federal/ Estatal": [self.subsistema.nombre],
            "Trámite Inicial o prórroga": ["Trámite inicial"],
            "Nombre del trabajador": ["Juan Pérez"],
            "DIAGNOSTICO": [""],
            "Nombre del sindicato": [""],
            "Contacto del trabajador y/o sindicato": [""],
            "Número de oficio del sindicato o escrito de origen": ["OF-123"],
            "Fecha de recepción del oficio del sindicato o escrito del trabajador en el nivel educativo": ["2024-01-10"],
            "Incidencias para la Integración del expediente/ prevención/ o contestación negativa del trámite": [""],
            "Oficio de envío a la Subsecretaría / PRÓRROGAS de licencias": [""],
            "Fecha de recepción en la Subsecretaría /PRÓRROGAS de licencias": [""],
            "Incidencias para el visto bueno de la Subsecretaría": [""],
            "Número de oficio y fecha de Visto Bueno de la Subsecretaría": [""],
            "Oficio de envío a Recursos Humanos de la Secretaría de Administración y Finanzas del Gobierno del Estado": [""],
            "Fecha de recepción del área de Recursos Humanos": [""],
            "Número de oficio y fecha de la resolución emitida por Recursos Humanos de la Secretaría de Administración y Finanzas del Gobierno del Estado": [""],
            "RESULTADO DE LA RESOLUCIÓN EMITIDA POR RECURSOS HUMANOS": [self.resultado.nombre],
            "Número de oficio y fecha de notificacíon al sindicato sobre la resolución.": [""],
            "Número de oficio y fecha de la notificación al trabajador sobre la resolución.": [""],
            "Fecha en la se realizó la notificacion al sindicato": [""],
            "Fecha en la se realizó la notificación al trabajador": [""],
        }
        df = pd.DataFrame(datos)
        resultado = import_csv.cargar_desde_dataframe(df, crear_catalogos=False)
        self.assertEqual(resultado.resumen["errores"], 1)
        self.assertEqual(models.Tramite.objects.count(), 0)

