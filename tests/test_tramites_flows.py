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
    MAX_LISTADO_QUERIES = 30

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
                "view_tramitecaso",
                "change_tramitecaso",
                "delete_tramitecaso",
            ],
            content_type__app_label="licencias",
        )
        self.user.user_permissions.set(required_perms)
        self.client.force_login(self.user)

        self.cct = models.PlantillaCentroTrabajo.objects.create(
            cct="31ABC1234X",
            nombre="Secundaria Uno",
            asesor="Asesor 1",
            sostenimiento="Federal",
            subnivel="General",
        )
        self.estatus_abierto = models.EstatusCaso.objects.create(nombre="Abierto", orden=1)
        self.estatus_cerrado = models.EstatusCaso.objects.create(nombre="Cerrado", orden=2)
        self.estatus_tramite_a = models.EstatusTramite.objects.create(nombre="Turnado", orden=1)
        self.estatus_tramite_b = models.EstatusTramite.objects.create(nombre="Concluido", orden=2)
        self.tipo_inicial = models.TipoProceso.objects.create(nombre="Tipo A")

    def test_crear_tramite_registra_historial_inicial(self):
        payload = {
            "cct": self.cct.cct,
            "cct_codigo": self.cct.cct,
            "cct_nombre": self.cct.nombre,
            "cct_sistema": self.cct.sostenimiento,
            "cct_modalidad": self.cct.subnivel,
            "asesor_cct": self.cct.asesor,
            "fecha_apertura": date.today(),
            "estatus": self.estatus_abierto.pk,
            "tipo_inicial": self.tipo_inicial.pk,
            "asunto": "Trámite de prueba",
            "numero_oficio": "SE/001",
        }

        response = self.client.post(reverse("tramites:casointerno-create"), payload, follow=True)

        form = None
        if response.context:
            contexts = response.context if isinstance(response.context, list) else [response.context]
            for ctx in contexts:
                if ctx and "form" in ctx:
                    form = ctx["form"]
                    break
        if form:
            self.assertFalse(form.errors, form.errors)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(models.CasoInterno.objects.count(), 1)
        caso = models.CasoInterno.objects.get()
        self.assertEqual(caso.estatus, self.estatus_abierto)
        self.assertEqual(models.HistorialEstatusCaso.objects.filter(caso=caso).count(), 1)

    def test_crear_tramite_doble_post_con_mismo_submission_uid_no_duplica(self):
        get_response = self.client.get(reverse("tramites:casointerno-create"))
        self.assertEqual(get_response.status_code, 200)
        submission_uid = ""
        if get_response.context:
            contexts = (
                get_response.context if isinstance(get_response.context, list) else [get_response.context]
            )
            for ctx in contexts:
                token = (ctx or {}).get("submission_uid")
                if token:
                    submission_uid = token
                    break
        self.assertTrue(submission_uid)

        payload = {
            "cct": self.cct.cct,
            "cct_codigo": self.cct.cct,
            "cct_nombre": self.cct.nombre,
            "cct_sistema": self.cct.sostenimiento,
            "cct_modalidad": self.cct.subnivel,
            "asesor_cct": self.cct.asesor,
            "fecha_apertura": date.today(),
            "estatus": self.estatus_abierto.pk,
            "tipo_inicial": self.tipo_inicial.pk,
            "asunto": "Registro idempotente",
            "numero_oficio": "SE/002",
            "submission_uid": submission_uid,
        }

        first_response = self.client.post(reverse("tramites:casointerno-create"), payload, follow=True)
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(models.CasoInterno.objects.count(), 1)
        caso = models.CasoInterno.objects.get()
        self.assertEqual(caso.request_uid, submission_uid)

        second_response = self.client.post(reverse("tramites:casointerno-create"), payload, follow=True)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(models.CasoInterno.objects.count(), 1)
        self.assertContains(second_response, "Se evitó registrar un duplicado.")

    def test_editar_tramite_cambia_estatus_y_bitacora(self):
        caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Original",
        )

        payload = {
            "cct": self.cct.cct,
            "cct_codigo": self.cct.cct,
            "cct_nombre": self.cct.nombre,
            "cct_sistema": self.cct.sostenimiento,
            "cct_modalidad": self.cct.subnivel,
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

        form = None
        if response.context:
            contexts = response.context if isinstance(response.context, list) else [response.context]
            for ctx in contexts:
                if ctx and "form" in ctx:
                    form = ctx["form"]
                    break
        if form:
            self.assertFalse(form.errors, form.errors)
        self.assertEqual(response.status_code, 200)
        caso.refresh_from_db()
        self.assertEqual(caso.estatus, self.estatus_cerrado)
        self.assertEqual(models.HistorialEstatusCaso.objects.filter(caso=caso).count(), 1)

    def test_listado_tramites_filtra_por_estatus_y_busqueda(self):
        caso_match = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
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
            cct_modalidad=self.cct.subnivel,
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

    def test_listado_busca_por_folio_generado_en_caso(self):
        caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Caso con folio generado",
        )
        folio = models.FolioRegistro.objects.create(
            anio=2026,
            prefijo="SE/TEST",
            numero=1,
            folio="SE/TEST/0001/2026",
            tipo="caso",
            creado_por=self.user,
        )
        folio.casos.add(caso)

        response = self.client.get(
            reverse("tramites:casointerno-list"),
            {"buscar": folio.folio},
        )

        self.assertEqual(response.status_code, 200)
        object_list = response.context_data["object_list"]
        self.assertIn(caso, list(object_list))

    def test_listado_busca_tramite_anexo_por_folio_generado(self):
        caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Caso base",
        )
        tramite = models.TramiteCaso.objects.create(
            caso=caso,
            tipo=self.tipo_inicial,
            estatus=self.estatus_tramite_a,
            fecha=date.today(),
            asunto="Trámite con folio generado",
        )
        folio = models.FolioRegistro.objects.create(
            anio=2026,
            prefijo="SE/TRM",
            numero=2,
            folio="SE/TRM/0002/2026",
            tipo="tramite",
            tramite=tramite,
            creado_por=self.user,
        )

        response = self.client.get(
            reverse("tramites:casointerno-list"),
            {"buscar": folio.folio},
        )

        self.assertEqual(response.status_code, 200)
        tramites_busqueda = response.context_data["tramites_busqueda"]
        self.assertIn(tramite, list(tramites_busqueda))

    def test_listado_renderiza_buscador_con_lupa_submit(self):
        response = self.client.get(reverse("tramites:casointerno-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="navbar-search"')
        self.assertContains(response, 'class="sg-search__submit"')
        self.assertContains(response, 'type="submit"')

    def test_listado_usa_select_related_en_queries(self):
        models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Optimización",
        )

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("tramites:casointerno-list"))
            self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(ctx),
            self.MAX_LISTADO_QUERIES,
            f"Demasiadas consultas en listado: {len(ctx)}",
        )

    def test_listado_no_dispara_queries_extra_al_acceder_relaciones(self):
        """Monitorea consultas para evitar regresiones de select_related en el listado."""
        models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
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
            queries_after_list = len(ctx)
            # Acceder a relaciones no debe generar consultas adicionales (select_related activo).
            for caso in casos:
                _ = caso.cct.nombre
                _ = caso.estatus.nombre
                _ = caso.tipo_inicial.nombre
            queries_after_related_access = len(ctx)

        self.assertEqual(
            queries_after_related_access,
            queries_after_list,
            "Acceder a relaciones del caso disparó consultas extra; falta select_related/prefetch.",
        )
        self.assertLessEqual(
            queries_after_related_access,
            self.MAX_LISTADO_QUERIES,
            f"Demasiadas consultas en listado: {queries_after_related_access}",
        )

    def test_agregar_estatus_caso_guarda_fecha_estatus(self):
        caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Caso para estatus",
        )
        fecha_estatus = date(2026, 2, 10)

        response = self.client.post(
            reverse("tramites:casointerno-estatus-create", kwargs={"pk": caso.pk}),
            {
                "estatus_nuevo": str(self.estatus_cerrado.pk),
                "fecha_estatus": fecha_estatus.isoformat(),
                "comentario": "Cambio manual con fecha de estatus.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        cambio = models.HistorialEstatusCaso.objects.filter(caso=caso).order_by("-id").first()
        self.assertIsNotNone(cambio)
        self.assertEqual(cambio.fecha_estatus, fecha_estatus)

    def test_agregar_estatus_tramite_guarda_fecha_estatus(self):
        caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Caso base para trámite",
        )
        tramite = models.TramiteCaso.objects.create(
            caso=caso,
            tipo=self.tipo_inicial,
            estatus=self.estatus_tramite_a,
            fecha=date.today(),
            asunto="Trámite para prueba de estatus",
        )
        fecha_estatus = date(2026, 2, 11)

        response = self.client.post(
            reverse(
                "tramites:tramite-caso-estatus-create",
                kwargs={"caso_pk": caso.pk, "tramite_pk": tramite.pk},
            ),
            {
                "estatus_nuevo": str(self.estatus_tramite_b.pk),
                "fecha_estatus": fecha_estatus.isoformat(),
                "comentario": "Cambio de estatus en trámite con fecha controlada.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        cambio = (
            models.HistorialEstatusTramiteCaso.objects.filter(tramite=tramite).order_by("-id").first()
        )
        self.assertIsNotNone(cambio)
        self.assertEqual(cambio.fecha_estatus, fecha_estatus)

    def test_eliminar_tramite_no_revienta_por_fk_en_bitacora(self):
        caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_abierto,
            tipo_inicial=self.tipo_inicial,
            asunto="Caso para eliminar trámite",
        )
        tramite = models.TramiteCaso.objects.create(
            caso=caso,
            tipo=self.tipo_inicial,
            estatus=self.estatus_tramite_a,
            fecha=date.today(),
            asunto="Trámite que se eliminará",
        )

        response = self.client.post(
            reverse("tramites:tramite-caso-delete", kwargs={"caso_pk": caso.pk, "pk": tramite.pk}),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(models.TramiteCaso.objects.filter(pk=tramite.pk).exists())
        eliminado = (
            models.BitacoraCambioCritico.objects.filter(
                modulo="tramite",
                accion="eliminado",
                object_id=tramite.pk,
            )
            .order_by("-id")
            .first()
        )
        self.assertIsNotNone(eliminado)
        self.assertIsNone(eliminado.tramite_id)
        self.assertEqual(eliminado.caso_id, caso.pk)
