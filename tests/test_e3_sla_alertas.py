from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tramites import models
from tramites.services import jobs
from tramites.services import sla as sla_service


class E3SlaAlertasTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="operador_e3",
            email="operador_e3@example.com",
            password="password",
            is_staff=True,
        )
        self.supervisor = user_model.objects.create_user(
            username="supervisor_e3",
            email="supervisor_e3@example.com",
            password="password",
            is_staff=True,
        )
        self.escalation_group = Group.objects.create(name="Coordinacion SLA E3")
        self.escalation_group.user_set.add(self.supervisor)
        perms = Permission.objects.filter(
            codename__in=[
                "view_casointerno",
                "view_tramitecaso",
                "change_casointerno",
                "change_tramitecaso",
            ],
            content_type__app_label="licencias",
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)

        self.cct = models.PlantillaCentroTrabajo.objects.create(
            cct="31E3C0001A",
            nombre="Secundaria E3",
            asesor="Asesor E3",
            sostenimiento="Federal",
            subnivel="General",
        )
        self.tipo = models.TipoProceso.objects.create(nombre="Tipo E3")
        self.estatus_caso = models.EstatusCaso.objects.create(nombre="En proceso E3", orden=1)
        self.estatus_tramite = models.EstatusTramite.objects.create(nombre="Turnado E3", orden=1)

    def _create_case(self, **overrides) -> models.CasoInterno:
        payload = {
            "cct": self.cct,
            "cct_nombre": self.cct.nombre,
            "cct_sistema": self.cct.sostenimiento,
            "cct_modalidad": self.cct.subnivel,
            "asesor_cct": self.cct.asesor,
            "fecha_apertura": timezone.localdate(),
            "estatus": self.estatus_caso,
            "tipo_inicial": self.tipo,
            "asunto": "Caso E3",
            "creado_por": self.user,
        }
        payload.update(overrides)
        caso = models.CasoInterno.objects.create(**payload)
        caso.usuarios_involucrados.add(self.user)
        return caso

    def _create_tramite(self, caso: models.CasoInterno, **overrides) -> models.TramiteCaso:
        payload = {
            "caso": caso,
            "tipo": self.tipo,
            "estatus": self.estatus_tramite,
            "fecha": timezone.localdate(),
            "asunto": "Trámite E3",
        }
        payload.update(overrides)
        tramite = models.TramiteCaso.objects.create(**payload)
        tramite.usuarios_involucrados.add(self.user)
        return tramite

    def test_motor_calcula_vencimiento_riesgo_y_semaforo(self):
        models.SLARegla.objects.create(
            ambito=models.SLARegla.AMBITO_CASO,
            tipo_proceso=self.tipo,
            dias_objetivo=3,
            dias_alerta_amarilla=1,
            dias_escalamiento=2,
            peso_riesgo=60,
        )
        caso = self._create_case(fecha_apertura=timezone.localdate() - timedelta(days=4))
        snapshot = sla_service.build_sla_snapshot_for_case(caso, today=timezone.localdate())
        self.assertEqual(snapshot["fecha_vencimiento"], caso.fecha_apertura + timedelta(days=3))
        self.assertEqual(snapshot["semaforo"], "rojo")
        self.assertTrue(snapshot["es_vencido"])
        self.assertGreaterEqual(snapshot["riesgo_score"], 120)

    def test_semaforo_es_consistente_en_listado_y_detalle(self):
        models.SLARegla.objects.create(
            ambito=models.SLARegla.AMBITO_CASO,
            tipo_proceso=self.tipo,
            dias_objetivo=2,
            dias_alerta_amarilla=2,
        )
        models.SLARegla.objects.create(
            ambito=models.SLARegla.AMBITO_TRAMITE,
            tipo_proceso=self.tipo,
            dias_objetivo=2,
            dias_alerta_amarilla=1,
        )
        caso = self._create_case(fecha_apertura=timezone.localdate())
        tramite = self._create_tramite(caso=caso, fecha=timezone.localdate() - timedelta(days=3))

        list_response = self.client.get(reverse("tramites:casointerno-list"))
        self.assertEqual(list_response.status_code, 200)
        listed_case = next(item for item in list_response.context["casos"] if item.pk == caso.pk)
        listed_tramite = next(
            item for item in list_response.context["tramites_busqueda"] if item.pk == tramite.pk
        )
        self.assertEqual(listed_case.sla_snapshot["semaforo"], "amarillo")
        self.assertEqual(listed_tramite.sla_snapshot["semaforo"], "rojo")

        case_detail = self.client.get(reverse("tramites:casointerno-detail", args=[caso.pk]))
        self.assertEqual(case_detail.status_code, 200)
        self.assertEqual(case_detail.context["caso_sla"]["semaforo"], "amarillo")

        tramite_detail = self.client.get(
            reverse("tramites:tramite-caso-detail", kwargs={"caso_pk": caso.pk, "pk": tramite.pk})
        )
        self.assertEqual(tramite_detail.status_code, 200)
        self.assertEqual(tramite_detail.context["tramite_sla"]["semaforo"], "rojo")

    def test_alertas_sla_se_generan_con_dedupe_y_auditoria(self):
        models.SLARegla.objects.create(
            ambito=models.SLARegla.AMBITO_CASO,
            tipo_proceso=self.tipo,
            dias_objetivo=1,
            dias_alerta_amarilla=1,
            peso_riesgo=55,
        )
        caso = self._create_case(fecha_apertura=timezone.localdate())

        result_first = sla_service.run_sla_alert_scan()
        self.assertGreaterEqual(result_first["alertas_amarillas"], 1)
        self.assertTrue(
            models.BandejaNotificacion.objects.filter(
                evento="sla_alerta",
                caso=caso,
            ).exists()
        )
        self.assertTrue(
            models.SLAAlertaRegistro.objects.filter(
                caso=caso,
                tipo_alerta=models.SLAAlertaRegistro.ALERTA_AMARILLA,
            ).exists()
        )
        self.assertTrue(
            models.EventoSistema.objects.filter(
                descripcion="Alerta SLA amarilla generada",
                caso=caso,
            ).exists()
        )

        result_second = sla_service.run_sla_alert_scan()
        self.assertEqual(result_second["alertas_amarillas"], 0)
        self.assertEqual(
            models.SLAAlertaRegistro.objects.filter(
                caso=caso,
                tipo_alerta=models.SLAAlertaRegistro.ALERTA_AMARILLA,
            ).count(),
            1,
        )

    def test_escalamiento_respeta_roles_y_job_handler(self):
        models.SLARegla.objects.create(
            ambito=models.SLARegla.AMBITO_CASO,
            tipo_proceso=self.tipo,
            dias_objetivo=1,
            dias_alerta_amarilla=1,
            dias_escalamiento=1,
            grupo_escalamiento=self.escalation_group,
            peso_riesgo=75,
        )
        caso = self._create_case(fecha_apertura=timezone.localdate() - timedelta(days=3))

        jobs.enqueue_job(job_type="sla_alert_scan", payload={"source": "test"})
        processed = jobs.run_pending_jobs(limit=1, worker_name="test-worker-e3")
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0].estado, "exitoso")
        self.assertIn("escalamientos", processed[0].resultado)

        self.assertTrue(
            models.SLAAlertaRegistro.objects.filter(
                caso=caso,
                tipo_alerta=models.SLAAlertaRegistro.ALERTA_ESCALAMIENTO,
            ).exists()
        )
        self.assertTrue(
            models.BandejaNotificacionDestinatario.objects.filter(
                usuario=self.supervisor,
                notificacion__evento="sla_escalamiento",
                notificacion__caso=caso,
            ).exists()
        )
        self.assertTrue(
            models.EventoSistema.objects.filter(
                descripcion="Escalamiento SLA generado",
                caso=caso,
            ).exists()
        )
