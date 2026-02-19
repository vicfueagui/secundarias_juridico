from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from tramites import models


class E5ColaboracionInternaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.actor = User.objects.create_user(
            username="actor.e5",
            email="actor.e5@example.com",
            password="password",
        )
        self.mencionado = User.objects.create_user(
            username="mencion.e5",
            email="mencion.e5@example.com",
            password="password",
        )
        self.responsable = User.objects.create_user(
            username="responsable.e5",
            email="responsable.e5@example.com",
            password="password",
        )
        self.externo = User.objects.create_user(
            username="externo.e5",
            email="externo.e5@example.com",
            password="password",
        )

        permisos = Permission.objects.filter(
            codename__in=["view_casointerno", "change_casointerno"],
            content_type__app_label="licencias",
        )
        self.actor.user_permissions.set(permisos)
        self.responsable.user_permissions.set(permisos)

        self.cct = models.PlantillaCentroTrabajo.objects.create(
            cct="31E5T0001A",
            nombre="Secundaria E5",
            asesor="Asesor E5",
            sostenimiento="Federal",
            subnivel="General",
        )
        self.estatus = models.EstatusCaso.objects.create(nombre="Abierto E5", orden=1)
        self.tipo = models.TipoProceso.objects.create(nombre="Tipo E5")
        self.caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus,
            tipo_inicial=self.tipo,
            asunto="Expediente E5",
        )
        self.caso.usuarios_involucrados.set([self.actor, self.mencionado, self.responsable])

    def test_comentario_con_mencion_crea_trazabilidad_y_notificacion(self):
        self.client.force_login(self.actor)
        response = self.client.post(
            reverse("tramites:casointerno-comentario-create", kwargs={"pk": self.caso.pk}),
            {
                "mensaje": "Revisar evidencias para el acuerdo @mencion.e5",
                "next": reverse("tramites:casointerno-detail", kwargs={"pk": self.caso.pk}),
            },
        )

        self.assertEqual(response.status_code, 302)
        comentario = models.CasoComentarioInterno.objects.get(caso=self.caso)
        self.assertEqual(comentario.autor, self.actor)
        self.assertEqual(list(comentario.menciones.values_list("pk", flat=True)), [self.mencionado.pk])
        self.assertTrue(
            models.BandejaNotificacionDestinatario.objects.filter(
                usuario=self.mencionado,
                notificacion__evento="caso_mencion",
                notificacion__caso=self.caso,
            ).exists()
        )
        self.assertTrue(
            models.BitacoraCambioCritico.objects.filter(
                modulo="caso",
                accion="creado",
                caso_id=self.caso.pk,
                descripcion__icontains="Comentario interno agregado",
            ).exists()
        )

    def test_comentario_rechaza_mencion_de_usuario_no_autorizado(self):
        self.client.force_login(self.actor)
        response = self.client.post(
            reverse("tramites:casointerno-comentario-create", kwargs={"pk": self.caso.pk}),
            {
                "mensaje": "Este usuario no pertenece al expediente @externo.e5",
                "next": reverse("tramites:casointerno-detail", kwargs={"pk": self.caso.pk}),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(models.CasoComentarioInterno.objects.filter(caso=self.caso).exists())
        self.assertFalse(
            models.BandejaNotificacionDestinatario.objects.filter(
                notificacion__evento="caso_mencion",
                notificacion__caso=self.caso,
            ).exists()
        )

    def test_tarea_interna_con_completado_registra_auditoria(self):
        self.client.force_login(self.actor)
        compromiso = date.today() + timedelta(days=2)
        create_response = self.client.post(
            reverse("tramites:casointerno-tarea-create", kwargs={"pk": self.caso.pk}),
            {
                "titulo": "Enviar minuta interna",
                "descripcion": "Confirmar recepción con el área responsable.",
                "responsable": str(self.responsable.pk),
                "fecha_compromiso": compromiso.isoformat(),
                "next": reverse("tramites:casointerno-detail", kwargs={"pk": self.caso.pk}),
            },
        )

        self.assertEqual(create_response.status_code, 302)
        tarea = models.CasoTareaInterna.objects.get(caso=self.caso)
        self.assertEqual(tarea.estado, models.CasoTareaInterna.ESTADO_PENDIENTE)
        self.assertEqual(tarea.creada_por, self.actor)
        self.assertEqual(tarea.responsable, self.responsable)
        self.assertTrue(
            models.BandejaNotificacionDestinatario.objects.filter(
                usuario=self.responsable,
                notificacion__evento="caso_tarea_asignada",
                notificacion__caso=self.caso,
            ).exists()
        )

        self.client.force_login(self.responsable)
        complete_response = self.client.post(
            reverse(
                "tramites:casointerno-tarea-completar",
                kwargs={"pk": self.caso.pk, "tarea_pk": tarea.pk},
            ),
            {"next": reverse("tramites:casointerno-detail", kwargs={"pk": self.caso.pk})},
        )

        self.assertEqual(complete_response.status_code, 302)
        tarea.refresh_from_db()
        self.assertEqual(tarea.estado, models.CasoTareaInterna.ESTADO_COMPLETADA)
        self.assertEqual(tarea.completada_por, self.responsable)
        self.assertIsNotNone(tarea.completada_en)
        self.assertTrue(
            models.BitacoraCambioCritico.objects.filter(
                modulo="caso",
                accion="actualizado",
                caso_id=self.caso.pk,
                descripcion__icontains="Tarea interna completada",
            ).exists()
        )
        self.assertTrue(
            models.BandejaNotificacionDestinatario.objects.filter(
                usuario=self.actor,
                notificacion__evento="caso_tarea_completada",
                notificacion__caso=self.caso,
            ).exists()
        )
