from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tramites import models


class E2OperacionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operador_e2",
            email="operador_e2@example.com",
            password="password",
            is_staff=True,
        )
        self.other_user = get_user_model().objects.create_user(
            username="coordinador_e2",
            email="coordinador_e2@example.com",
            password="password",
            is_staff=True,
        )
        perms = Permission.objects.filter(
            codename__in=[
                "view_casointerno",
                "change_casointerno",
                "view_tramitecaso",
                "change_tramitecaso",
            ],
            content_type__app_label="licencias",
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)

        self.cct = models.PlantillaCentroTrabajo.objects.create(
            cct="31E2C0001A",
            nombre="Secundaria E2",
            asesor="Asesor E2",
            sostenimiento="Federal",
            subnivel="General",
        )
        self.tipo = models.TipoProceso.objects.create(nombre="Tipo E2")
        self.estatus_abierto = models.EstatusCaso.objects.create(nombre="Abierto E2", orden=1)
        self.estatus_cerrado = models.EstatusCaso.objects.create(nombre="Cerrado E2", orden=2)
        self.estatus_tramite_a = models.EstatusTramite.objects.create(nombre="Turnado E2", orden=1)
        self.estatus_tramite_b = models.EstatusTramite.objects.create(nombre="Concluido E2", orden=2)

    def _create_case(self, **overrides):
        payload = {
            "cct": self.cct,
            "cct_nombre": self.cct.nombre,
            "cct_sistema": self.cct.sostenimiento,
            "cct_modalidad": self.cct.subnivel,
            "asesor_cct": self.cct.asesor,
            "fecha_apertura": date.today(),
            "estatus": self.estatus_abierto,
            "tipo_inicial": self.tipo,
            "asunto": "Caso E2",
            "creado_por": self.user,
        }
        payload.update(overrides)
        caso = models.CasoInterno.objects.create(**payload)
        caso.usuarios_involucrados.add(self.user)
        return caso

    def test_dashboard_snapshot_shows_operational_counters(self):
        overdue_case = self._create_case(
            asunto="Vencido",
            fecha_termino=timezone.localdate() - timedelta(days=1),
        )
        stale_case = self._create_case(asunto="Sin movimiento")
        due_soon_case = self._create_case(
            asunto="Crítico",
            fecha_termino=timezone.localdate() + timedelta(days=1),
        )
        models.CasoInterno.objects.filter(pk=stale_case.pk).update(
            actualizado_en=timezone.now() - timedelta(days=7)
        )

        response = self.client.get(reverse("tramites:home"))
        self.assertEqual(response.status_code, 200)
        snapshot = response.context["snapshot_operacion"]
        self.assertGreaterEqual(snapshot["criticos_total"], 2)
        self.assertEqual(snapshot["vencidos_total"], 1)
        self.assertEqual(snapshot["sin_movimiento_total"], 1)
        queue = snapshot["queue_items"]
        self.assertTrue(queue)
        self.assertEqual(queue[0]["id"], overdue_case.pk)
        self.assertEqual(queue[0]["tipo"], "caso")
        self.assertEqual(queue[1]["id"], due_soon_case.pk)

    def test_saved_filters_can_be_created_and_deleted(self):
        response = self.client.post(
            reverse("tramites:filtro-guardado"),
            {
                "action": "save",
                "nombre": "Pendientes asesor",
                "alcance": models.FiltroGuardadoUsuario.ALCANCE_CASOS_LISTADO,
                "querystring": "estatus=1&buscar=ABC&page=2&hack=1",
                "next": reverse("tramites:casointerno-list"),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        filtro = models.FiltroGuardadoUsuario.objects.get(nombre="Pendientes asesor")
        self.assertIn("estatus=1", filtro.query_string)
        self.assertIn("buscar=ABC", filtro.query_string)
        self.assertNotIn("hack=1", filtro.query_string)
        self.assertNotIn("page=2", filtro.query_string)

        response = self.client.post(
            reverse("tramites:filtro-guardado"),
            {
                "action": "delete",
                "filter_id": str(filtro.pk),
                "next": reverse("tramites:casointerno-list"),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(models.FiltroGuardadoUsuario.objects.filter(pk=filtro.pk).exists())

    def test_quick_actions_assign_and_change_status_with_audit(self):
        caso = self._create_case(asunto="Caso acciones rápidas")

        response = self.client.post(
            reverse("tramites:operacion-accion-rapida"),
            {
                "action": "asignar",
                "target_type": "caso",
                "target_id": str(caso.pk),
                "usuario_asignado": str(self.other_user.pk),
                "next": reverse("tramites:home"),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(caso.usuarios_involucrados.filter(pk=self.other_user.pk).exists())
        self.assertTrue(
            models.BitacoraCambioCritico.objects.filter(
                modulo="caso",
                accion="actualizado",
                caso_id=caso.pk,
            ).exists()
        )

        response = self.client.post(
            reverse("tramites:operacion-accion-rapida"),
            {
                "action": "cambiar_estatus",
                "target_type": "caso",
                "target_id": str(caso.pk),
                "estatus_caso": str(self.estatus_cerrado.pk),
                "next": reverse("tramites:home"),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        caso.refresh_from_db()
        self.assertEqual(caso.estatus, self.estatus_cerrado)
        self.assertTrue(models.HistorialEstatusCaso.objects.filter(caso=caso).exists())
        self.assertTrue(
            models.BitacoraCambioCritico.objects.filter(
                modulo="estatus",
                accion="cambio_estatus",
                caso_id=caso.pk,
            ).exists()
        )

    def test_queue_filters_only_overdue_items(self):
        overdue_case = self._create_case(
            asunto="Caso vencido",
            fecha_termino=timezone.localdate() - timedelta(days=2),
        )
        active_case = self._create_case(
            asunto="Caso activo",
            fecha_termino=timezone.localdate() + timedelta(days=5),
        )
        tramite = models.TramiteCaso.objects.create(
            caso=active_case,
            tipo=self.tipo,
            estatus=self.estatus_tramite_a,
            fecha=timezone.localdate(),
            fecha_termino=timezone.localdate() - timedelta(days=1),
            asunto="Trámite vencido",
        )
        tramite.usuarios_involucrados.add(self.user)

        response = self.client.get(reverse("tramites:mi-cola"), {"estado": "vencidos"})
        self.assertEqual(response.status_code, 200)
        items = response.context["cola_items"]
        ids = {(item["tipo"], item["id"]) for item in items}
        self.assertIn(("caso", overdue_case.pk), ids)
        self.assertIn(("tramite", tramite.pk), ids)
        self.assertNotIn(("caso", active_case.pk), ids)
        self.assertTrue(all(item["is_overdue"] for item in items))

    def test_quick_action_requires_change_permission(self):
        self.user.user_permissions.clear()
        caso = self._create_case(asunto="Sin permiso")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("tramites:operacion-accion-rapida"),
            {
                "action": "asignar",
                "target_type": "caso",
                "target_id": str(caso.pk),
                "usuario_asignado": str(self.other_user.pk),
                "next": reverse("tramites:home"),
            },
        )
        self.assertEqual(response.status_code, 403)
