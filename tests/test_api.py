from __future__ import annotations

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from licencias import models


class TramiteAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester", password="secret"
        )
        self.client.force_authenticate(user=self.user)

        self.subsistema = models.Subsistema.objects.create(nombre="Federal")
        self.tipo_tramite = models.TipoTramite.objects.create(nombre="Licencia 754")
        self.etapa = models.Etapa.objects.create(nombre="Ingreso", orden=1)

        self.tramite = models.Tramite.objects.create(
            tipo_tramite=self.tipo_tramite,
            subsistema=self.subsistema,
            tramite_inicial_o_prorroga=models.Tramite.TipoSolicitud.INICIAL,
            trabajador_nombre="Juan Pérez",
            estado_actual=self.etapa,
            user_responsable=self.user,
        )

    def test_listado_tramites(self):
        url = reverse("licencias_api:tramite-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["folio"], self.tramite.folio)

    def test_filtra_por_folio(self):
        url = reverse("licencias_api:tramite-list")
        response = self.client.get(url, {"folio": self.tramite.folio})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

