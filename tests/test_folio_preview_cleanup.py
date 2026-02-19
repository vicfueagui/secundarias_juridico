from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from tramites import models


class FolioPreviewCleanupTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester_folio_cleanup",
            email="tester_folio_cleanup@example.com",
            password="password",
            is_staff=True,
        )
        perms = Permission.objects.filter(
            codename__in=[
                "add_folioregistro",
                "add_casointerno",
                "add_tramitecaso",
            ],
            content_type__app_label="licencias",
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)

        self.cct = models.PlantillaCentroTrabajo.objects.create(
            cct="31FOC0001X",
            nombre="Secundaria Folios",
            asesor="Asesor Folio",
            sostenimiento="Federal",
            subnivel="Secundaria",
        )
        self.estatus_caso = models.EstatusCaso.objects.create(nombre="Abierto", orden=1)
        self.tipo_inicial = models.TipoProceso.objects.create(nombre="Tipo Folio")
        self.caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_caso,
            tipo_inicial=self.tipo_inicial,
            asunto="Caso para pruebas de folio",
        )

    def _crear_folio_preview(self, *, tipo: str = "caso") -> models.FolioRegistro:
        seq = models.FolioRegistro.objects.count() + 1
        anio = date.today().year
        return models.FolioRegistro.objects.create(
            anio=anio,
            prefijo="SE/TEST",
            numero=seq,
            folio=f"SE/TEST/{seq}/{anio}",
            tipo=tipo,
            creado_por=self.user,
            activo=True,
        )

    def test_cancelar_preview_desactiva_folio_no_asociado(self):
        folio = self._crear_folio_preview()

        response = self.client.post(
            reverse("tramites:folio-generar-cancelar"),
            {"folio_ids": [str(folio.pk)]},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("cancelados"), 1)
        folio.refresh_from_db()
        self.assertFalse(folio.activo)
        self.assertIsNotNone(folio.eliminado_en)
        self.assertEqual(folio.eliminado_por_id, self.user.id)
        self.assertTrue(
            models.FolioActividad.objects.filter(
                folio=folio,
                accion="eliminado",
            ).exists()
        )

    def test_cancelar_preview_no_toca_folio_asociado(self):
        folio = self._crear_folio_preview()
        folio.casos.add(self.caso)

        response = self.client.post(
            reverse("tramites:folio-generar-cancelar"),
            {"folio_ids": [str(folio.pk)]},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("cancelados"), 0)
        folio.refresh_from_db()
        self.assertTrue(folio.activo)

    def test_create_caso_form_invalid_cancela_folio_preview(self):
        folio = self._crear_folio_preview(tipo="caso")

        response = self.client.post(
            reverse("tramites:casointerno-create"),
            {
                "folio_generado_id": str(folio.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        folio.refresh_from_db()
        self.assertFalse(folio.activo)

    def test_create_tramite_form_invalid_cancela_folio_preview(self):
        folio = self._crear_folio_preview(tipo="tramite")
        prefix = "tramite_caso"

        response = self.client.post(
            reverse("tramites:tramite-caso-create", kwargs={"caso_pk": self.caso.pk}),
            {
                f"{prefix}-folio_generado_id": str(folio.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        folio.refresh_from_db()
        self.assertFalse(folio.activo)
