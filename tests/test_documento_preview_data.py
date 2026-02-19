from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from tramites import models


class DocumentoPreviewDataTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester_preview_docs",
            email="tester_preview_docs@example.com",
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
            cct="31AAA9999A",
            nombre="Secundaria Vista Previa",
            asesor="Asesor Docs",
            sostenimiento="Federal",
            subnivel="Secundaria",
        )
        self.tipo = models.TipoProceso.objects.create(nombre="Seguimiento")
        self.estatus_caso = models.EstatusCaso.objects.create(nombre="Abierto", orden=1)
        self.estatus_tramite = models.EstatusTramite.objects.create(nombre="Recibido", orden=1)
        self.caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_caso,
            tipo_inicial=self.tipo,
            asunto="Caso sin adjuntos",
        )
        self.tramite = models.TramiteCaso.objects.create(
            caso=self.caso,
            tipo=self.tipo,
            estatus=self.estatus_tramite,
            fecha=date.today(),
            asunto="Trámite sin adjuntos",
        )

    def test_preview_data_caso_devuelve_payload(self):
        response = self.client.get(
            reverse("tramites:documento-preview-data"),
            {"tipo": "caso", "id": self.caso.pk},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tipo"], "caso")
        self.assertEqual(payload["id"], self.caso.pk)
        self.assertEqual(payload["documentos"], [])

    def test_preview_data_tramite_devuelve_payload(self):
        response = self.client.get(
            reverse("tramites:documento-preview-data"),
            {"tipo": "tramite", "id": self.tramite.pk, "caso_id": self.caso.pk},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tipo"], "tramite")
        self.assertEqual(payload["id"], self.tramite.pk)
        self.assertEqual(payload["documentos"], [])

    def test_listado_renderiza_boton_de_vista_previa(self):
        response = self.client.get(reverse("tramites:casointerno-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-doc-preview-open")
        self.assertContains(response, reverse("tramites:documento-preview-data"))
