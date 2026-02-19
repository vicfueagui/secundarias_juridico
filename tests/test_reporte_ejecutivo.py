from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from tramites import models


class ReporteEjecutivoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester_reporte",
            email="tester_reporte@example.com",
            password="password",
            is_staff=True,
        )
        permisos = Permission.objects.filter(
            codename__in=["view_casointerno", "view_tramitecaso"],
            content_type__app_label="licencias",
        )
        self.user.user_permissions.set(permisos)
        self.client.force_login(self.user)

        self.cct = models.PlantillaCentroTrabajo.objects.create(
            cct="31AAA0001A",
            nombre="Secundaria Tecnica Uno",
            asesor="Asesor Juridico",
            sostenimiento="Federal",
            subnivel="Secundaria",
        )
        self.tipo = models.TipoProceso.objects.create(nombre="Analisis Juridico")
        self.estatus_caso = models.EstatusCaso.objects.create(nombre="En revision", orden=1)
        self.estatus_tramite = models.EstatusTramite.objects.create(nombre="Turnado", orden=1)

        self.caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            descripcion_breve="Caso ejecutivo de prueba",
            fecha_apertura=date.today(),
            estatus=self.estatus_caso,
            tipo_inicial=self.tipo,
            asunto="Revision de expediente",
            numero_oficio="SE/REP/001/2026",
        )
        models.HistorialEstatusCaso.objects.create(
            caso=self.caso,
            estatus_anterior=None,
            estatus_nuevo=self.estatus_caso,
            usuario=self.user,
            comentario="Alta inicial",
        )

        self.tramite = models.TramiteCaso.objects.create(
            caso=self.caso,
            tipo=self.tipo,
            estatus=self.estatus_tramite,
            fecha=date.today(),
            asunto="Seguimiento anexo",
            numero_oficio="SE/REP/001-A/2026",
            es_iniciador=False,
        )
        models.HistorialEstatusTramiteCaso.objects.create(
            tramite=self.tramite,
            estatus_anterior=None,
            estatus_nuevo=self.estatus_tramite,
            usuario=self.user,
            comentario="Registro de tramite anexo",
        )

    def test_reporte_ejecutivo_caso_muestra_datos_integrales(self):
        response = self.client.get(
            reverse("tramites:casointerno-reporte-ejecutivo", kwargs={"pk": self.caso.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Caso #{self.caso.pk}")
        self.assertContains(response, "Construccion cronologica del caso")
        self.assertContains(response, f"Tramite #{self.tramite.pk}")
        self.assertContains(response, self.estatus_tramite.nombre)

    def test_reporte_ejecutivo_desde_tramite_indica_origen(self):
        response = self.client.get(
            reverse(
                "tramites:tramite-caso-reporte-ejecutivo",
                kwargs={"caso_pk": self.caso.pk, "pk": self.tramite.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Resumen de tramite anexo #{self.tramite.pk}")
        self.assertContains(response, "Tramite del resumen actual")

    def test_detalles_incluyen_boton_a_reporte_ejecutivo(self):
        response_caso = self.client.get(
            reverse("tramites:casointerno-detail", kwargs={"pk": self.caso.pk})
        )
        self.assertEqual(response_caso.status_code, 200)
        self.assertContains(
            response_caso,
            reverse("tramites:casointerno-reporte-ejecutivo", kwargs={"pk": self.caso.pk}),
        )

        response_tramite = self.client.get(
            reverse(
                "tramites:tramite-caso-detail",
                kwargs={"caso_pk": self.caso.pk, "pk": self.tramite.pk},
            )
        )
        self.assertEqual(response_tramite.status_code, 200)
        self.assertContains(
            response_tramite,
            reverse(
                "tramites:tramite-caso-reporte-ejecutivo",
                kwargs={"caso_pk": self.caso.pk, "pk": self.tramite.pk},
            ),
        )
