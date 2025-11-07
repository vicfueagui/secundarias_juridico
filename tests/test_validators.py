from __future__ import annotations

from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from licencias import models
from licencias.services import validators


class ValidatorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.subsistema = models.Subsistema.objects.create(nombre="Federal")
        cls.tipo_tramite = models.TipoTramite.objects.create(nombre="Licencia 754")
        cls.diagnostico = models.Diagnostico.objects.create(nombre="Diagnóstico A")
        cls.sindicato = models.Sindicato.objects.create(nombre="SNTE")
        cls.resultado = models.Resultado.objects.create(nombre="Procedente")
        cls.etapa_ingreso = models.Etapa.objects.create(nombre="Ingreso", orden=1)
        cls.etapa_resolucion = models.Etapa.objects.create(nombre="Resolución", orden=3)

    def _tramite_base(self, **kwargs) -> models.Tramite:
        datos = {
            "tipo_tramite": self.tipo_tramite,
            "subsistema": self.subsistema,
            "tramite_inicial_o_prorroga": models.Tramite.TipoSolicitud.INICIAL,
            "trabajador_nombre": "Juan Pérez",
            "diagnostico": self.diagnostico,
            "sindicato": self.sindicato,
            "estado_actual": self.etapa_ingreso,
        }
        datos.update(kwargs)
        return models.Tramite(**datos)

    def test_validar_fechas_chronologicas_detecta_inconsistencia(self):
        tramite = self._tramite_base(
            fecha_recepcion_nivel=date(2024, 5, 10),
            fecha_recepcion_subsecretaria=date(2024, 5, 2),
        )
        with self.assertRaises(ValidationError):
            validators.validar_fechas_chronologicas(tramite)

    def test_validar_campos_por_etapa_exige_resolucion(self):
        tramite = self._tramite_base(estado_actual=self.etapa_resolucion)
        with self.assertRaises(ValidationError):
            validators.validar_campos_por_etapa(tramite)

    def test_validar_transicion_etapa_no_permite_saltos_invalidos(self):
        with self.assertRaises(ValidationError):
            validators.validar_transicion_etapa(
                self.etapa_ingreso, self.etapa_resolucion
            )

