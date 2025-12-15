from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.db import connection

from tramites import models


class TramitesFlowTests(TestCase):
    """Flujos críticos del módulo /tramites/ (Definition of Done en CI)."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester",
            email="tester@example.com",
            password="password",
            is_staff=True,
        )
        required_perms = Permission.objects.filter(
            codename__in=[
                "view_casointerno",
                "add_casointerno",
                "change_casointerno",
            ],
            content_type__app_label="licencias",
        )
        self.user.user_permissions.set(required_perms)
        self.client.force_login(self.user)

        self.cct = models.CCTSecundaria.objects.create(
            cct="ABC1234567",
            nombre="Secundaria Uno",
            asesor="Asesor 1",
            servicio="General",
            sostenimiento="Federal",
        )
        self.estatus_abierto = models.EstatusCaso.objects.create(nombre="Abierto", orden=1)
        self.estatus_cerrado = models.EstatusCaso.objects.create(nombre="Cerrado", orden=2)
        self.tipo_inicial = models.TipoProceso.objects.create(nombre="Tipo A")

    def test_crear_tramite_registra_historial_inicial(self):
        payload = {
            "cct": self.cct.pk,
            "cct_nombre": self.cct.nombre,
            "cct_sistema": self.cct.sostenimiento,
            "cct_modalidad": self.cct.servicio,
            "asesor_cct": self.cct.asesor,
            "fecha_apertura": date.today(),
            "estatus": self.estatus_abierto.pk,
            "tipo_inicial": self.tipo_inicial.pk,
            "asunto": "Trámite de prueba",
            "numero_oficio": "SE/001",
        }

        response = self.client.post(reverse("tramites:casointerno-create"), payload, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(models.CasoInterno.objects.count(), 1)
        caso = models.CasoInterno.objects.get()
        self.assertEqual(caso.estatus, self.estatus_abierto)
        self.assertEqual(models.HistorialEstatusCaso.objects.filter(caso=caso).count(), 1)

    def test_editar_tramite_cambia_estatus_y_bitacora(self):
        caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.servicio,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Original",
        )

        payload = {
            "cct": self.cct.pk,
            "cct_nombre": self.cct.nombre,
            "cct_sistema": self.cct.sostenimiento,
            "cct_modalidad": self.cct.servicio,
            "asesor_cct": self.cct.asesor,
            "fecha_apertura": date.today(),
            "estatus": self.estatus_cerrado.pk,
            "tipo_inicial": self.tipo_inicial.pk,
            "asunto": "Actualizado",
            "numero_oficio": "",
        }

        response = self.client.post(
            reverse("tramites:casointerno-update", kwargs={"pk": caso.pk}),
            payload,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        caso.refresh_from_db()
        self.assertEqual(caso.estatus, self.estatus_cerrado)
        self.assertEqual(models.HistorialEstatusCaso.objects.filter(caso=caso).count(), 1)

    def test_listado_tramites_filtra_por_estatus_y_busqueda(self):
        caso_match = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.servicio,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Caso buscado",
            folio_inicial="F-123",
        )
        models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.servicio,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_cerrado,
            tipo_inicial=self.tipo_inicial,
            asunto="Otro caso",
        )

        response = self.client.get(
            reverse("tramites:casointerno-list"),
            {"estatus": self.estatus_abierto.pk, "buscar": "F-123"},
        )

        self.assertEqual(response.status_code, 200)
        object_list = response.context_data["object_list"]
        self.assertEqual(list(object_list), [caso_match])

    def test_listado_usa_select_related_en_queries(self):
        models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.servicio,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Optimización",
        )

        with self.assertNumQueries(10):
            response = self.client.get(reverse("tramites:casointerno-list"))
            self.assertEqual(response.status_code, 200)

    def test_listado_no_dispara_queries_extra_al_acceder_relaciones(self):
        """Monitorea consultas para evitar regresiones de select_related en el listado."""
        models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.servicio,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Con relaciones",
        )

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("tramites:casointerno-list"))
            self.assertEqual(response.status_code, 200)
            casos = list(response.context_data["object_list"])
            # Acceder a relaciones no debe generar consultas adicionales (select_related activo).
            for caso in casos:
                _ = caso.cct.nombre
                _ = caso.estatus.nombre
                _ = caso.tipo_inicial.nombre

        # Uso de select_related: la cantidad total debe mantenerse baja (<10).
        self.assertLessEqual(len(ctx), 10, f"Demasiadas consultas en listado: {len(ctx)}")
