from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from tramites import models, views
from tramites.services import data_quality, feature_flags, jobs


class FeatureFlagResolutionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ff_user",
            email="ff_user@example.com",
            password="password",
        )
        self.group = Group.objects.create(name="Revisores")
        self.user.groups.add(self.group)

    def test_group_override_disables_flag(self):
        flag = models.FeatureFlag.objects.create(
            codigo="module_demo",
            modulo="demo",
            nombre="Demo",
            habilitado=True,
            habilitado_por_defecto=True,
        )
        models.FeatureFlagGrupo.objects.create(flag=flag, grupo=self.group, habilitado=False)
        self.assertFalse(feature_flags.is_enabled("module_demo", self.user))

    def test_missing_flag_uses_safe_default_true(self):
        self.assertTrue(feature_flags.is_enabled("no_existe", self.user))


class DataQualityServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="quality_user",
            email="quality@example.com",
            password="password",
        )
        self.cct = models.PlantillaCentroTrabajo.objects.create(
            cct="31E1Q0001A",
            nombre="Secundaria Calidad",
            asesor="Asesor Calidad",
            sostenimiento="Federal",
            subnivel="General",
        )
        self.estatus = models.EstatusCaso.objects.create(nombre="Abierto", orden=1)
        self.tipo = models.TipoProceso.objects.create(nombre="Tipo Calidad")
        self.estatus_tramite = models.EstatusTramite.objects.create(nombre="Turnado", orden=1)
        self.estatus_licencia = models.EstatusLicencia.objects.create(nombre="En captura", orden=1)
        self.empleado = models.PlantillaEmpleado.objects.create(nombre="Trabajador Calidad", rfc="AAA010101AAA")

    def test_run_quality_scan_detects_all_issue_categories(self):
        # Incompleto + inconsistente.
        models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            fecha_termino=date.today() - timedelta(days=1),
            estatus=self.estatus,
            tipo_inicial=self.tipo,
            asunto="",
            numero_oficio="",
        )
        # Duplicados de caso.
        models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus,
            tipo_inicial=self.tipo,
            asunto="Caso 1",
            numero_oficio="DUP-001",
        )
        caso_dup = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus,
            tipo_inicial=self.tipo,
            asunto="Caso 2",
            numero_oficio="DUP-001",
        )
        # Duplicado de trámite.
        models.TramiteCaso.objects.create(
            caso=caso_dup,
            tipo=self.tipo,
            estatus=self.estatus_tramite,
            fecha=date.today(),
            asunto="Trámite A",
            numero_oficio="TR-DUP-01",
        )
        models.TramiteCaso.objects.create(
            caso=caso_dup,
            tipo=self.tipo,
            estatus=self.estatus_tramite,
            fecha=date.today(),
            asunto="Trámite B",
            numero_oficio="TR-DUP-01",
        )
        # Incompleto de licencia.
        models.LicenciaRegistro.objects.create(
            trabajador=self.empleado,
            tipo_tramite=models.TIPO_LICENCIA_CHOICES[0][0],
            tipo_prorroga=models.TIPO_PRORROGA_CHOICES[0][0],
            sindicato=models.SINDICATO_CHOICES[0][0],
            fecha_tramite=date.today(),
            numero_expediente="",
            estatus=self.estatus_licencia,
        )

        run = data_quality.run_quality_scan(actor=self.user, origen="manual")
        self.assertEqual(run.estado, "exitoso")

        categorias = set(
            models.DataQualityIssue.objects.filter(activo=True).values_list("categoria", flat=True)
        )
        self.assertIn("incompleto", categorias)
        self.assertIn("duplicado", categorias)
        self.assertIn("inconsistente", categorias)
        self.assertGreater(run.resumen.get("issues_detected", 0), 0)


class AsyncJobsInfrastructureTests(TestCase):
    def test_scheduler_and_worker_execute_healthcheck_job(self):
        scheduled = models.ScheduledJob.objects.create(
            codigo="test-healthcheck",
            nombre="Healthcheck test",
            handler="healthcheck",
            intervalo_minutos=5,
            activo=True,
            proxima_ejecucion=timezone.now() - timedelta(minutes=1),
        )
        created = jobs.schedule_due_jobs(limit=10)
        target_jobs = [item for item in created if item.scheduled_job_id == scheduled.pk]
        self.assertEqual(len(target_jobs), 1)
        self.assertEqual(target_jobs[0].estado, "pendiente")

        processed = jobs.run_pending_jobs(limit=10, worker_name="test-worker")
        self.assertGreaterEqual(len(processed), 1)
        target_jobs[0].refresh_from_db()
        self.assertEqual(target_jobs[0].estado, "exitoso")
        self.assertIn("ok", target_jobs[0].resultado)


class UnifiedEventsAuditTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="audit_user",
            email="audit_user@example.com",
            password="password",
        )
        self.cct = models.PlantillaCentroTrabajo.objects.create(
            cct="31AUD0001A",
            nombre="Secundaria Auditoría",
            asesor="Asesor Auditoría",
            sostenimiento="Federal",
            subnivel="General",
        )
        self.tipo = models.TipoProceso.objects.create(nombre="Tipo Auditoría")
        self.estatus_a = models.EstatusCaso.objects.create(nombre="Abierto audit", orden=1)
        self.estatus_b = models.EstatusCaso.objects.create(nombre="Cerrado audit", orden=2)
        self.caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_a,
            tipo_inicial=self.tipo,
            asunto="Caso auditoría",
        )

    def test_status_change_creates_unified_event_and_extended_audit(self):
        views.registrar_cambio_estatus_caso(
            caso=self.caso,
            usuario=self.user,
            estatus_anterior=self.estatus_a,
            estatus_nuevo=self.estatus_b,
            comentario="Cambio de prueba",
            notify=False,
        )
        self.assertTrue(
            models.BitacoraCambioCritico.objects.filter(
                modulo="estatus",
                accion="cambio_estatus",
                caso_id=self.caso.pk,
            ).exists()
        )
        self.assertTrue(
            models.EventoSistema.objects.filter(
                categoria="estatus",
                accion="cambio_estatus",
                caso_id=self.caso.pk,
            ).exists()
        )
