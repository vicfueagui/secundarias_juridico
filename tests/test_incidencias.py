from __future__ import annotations

from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from tramites import models, serializers


class IncidenciasLogicTests(TestCase):
    def setUp(self):
        self.cct = models.CCTSecundaria.objects.create(
            cct="TEST1234567",
            nombre="Secundaria de prueba",
            asesor="Asesor Incidencias",
            servicio="General",
            sostenimiento="Estatal",
        )
        self.estatus_abierto = models.EstatusCaso.objects.create(nombre="Abierto", orden=1)
        self.tipo_inicial = models.TipoProceso.objects.create(nombre="Tipo Incidencias")

    def build_caso(self, **kwargs):
        return models.CasoInterno(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.servicio,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date(2024, 1, 1),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Caso con incidencias",
            **kwargs,
        )

    def test_incidencias_issste_calculates_days(self):
        caso = self.build_caso(
            incidencia_afiliacion="ISSSTE",
            incidencia_fecha_inicio=date(2024, 1, 1),
            incidencia_fecha_termino=date(2024, 1, 5),
        )

        caso.full_clean()
        caso.save()

        self.assertEqual(caso.incidencia_dias_otorgados, 5)
        self.assertEqual(caso.incidencia_fecha_termino, date(2024, 1, 5))

    def test_incidencias_imss_calculates_fecha_termino(self):
        caso = self.build_caso(
            incidencia_afiliacion="IMSS",
            incidencia_fecha_inicio=date(2024, 2, 1),
            incidencia_dias_otorgados=3,
        )

        caso.full_clean()
        caso.save()

        self.assertEqual(caso.incidencia_fecha_termino, date(2024, 2, 3))
        self.assertEqual(caso.incidencia_dias_otorgados, 3)

    def test_incidencias_invalid_period_raises(self):
        caso = self.build_caso(
            incidencia_afiliacion="ISSSTE",
            incidencia_fecha_inicio=date(2024, 5, 10),
            incidencia_fecha_termino=date(2024, 5, 8),
        )

        with self.assertRaises(ValidationError):
            caso.full_clean()

    def test_tramite_caso_serializer_normalises_incidencias(self):
        caso = self.build_caso()
        caso.full_clean()
        caso.save()

        serializer = serializers.TramiteCasoSerializer(
            data={
                "caso": caso.pk,
                "tipo": self.tipo_inicial.pk,
                "fecha": date(2024, 3, 1),
                "numero_oficio": "",
                "asunto": "",
                "observaciones": "",
                "receptores_adicionales": [],
                "incidencia_afiliacion": "ISSSTE",
                "incidencia_fecha_inicio": date(2024, 3, 1),
                "incidencia_fecha_termino": date(2024, 3, 3),
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        validated = serializer.validated_data
        self.assertEqual(validated["incidencia_dias_otorgados"], 3)
