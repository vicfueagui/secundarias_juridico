from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tramites import models


class BandejaInboxViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="inbox_user",
            email="inbox_user@example.com",
            password="password",
        )
        self.client.force_login(self.user)

    def _crear_destinatario(self, *, indice: int, evento: str = "caso_creado", leido: bool = False):
        notificacion = models.BandejaNotificacion.objects.create(
            evento=evento,
            titulo=f"Notificación {indice}",
            mensaje="Mensaje de prueba",
        )
        return models.BandejaNotificacionDestinatario.objects.create(
            notificacion=notificacion,
            usuario=self.user,
            leido=leido,
        )

    def test_bandeja_lista_con_paginado_20(self):
        for indice in range(25):
            self._crear_destinatario(indice=indice)

        response = self.client.get(reverse("tramites:bandeja"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(response.context["paginator"].per_page, 20)
        self.assertEqual(len(response.context["entradas"]), 20)

        response_page_2 = self.client.get(reverse("tramites:bandeja"), {"page": 2})
        self.assertEqual(response_page_2.status_code, 200)
        self.assertEqual(len(response_page_2.context["entradas"]), 5)

    def test_bandeja_ordena_por_fecha_reciente_a_antigua(self):
        ahora = timezone.now()
        entrada_antigua = self._crear_destinatario(indice=1)
        entrada_media = self._crear_destinatario(indice=2)
        entrada_reciente = self._crear_destinatario(indice=3)

        models.BandejaNotificacion.objects.filter(pk=entrada_antigua.notificacion_id).update(
            creado_en=ahora - timedelta(days=3),
        )
        models.BandejaNotificacion.objects.filter(pk=entrada_media.notificacion_id).update(
            creado_en=ahora - timedelta(days=1),
        )
        models.BandejaNotificacion.objects.filter(pk=entrada_reciente.notificacion_id).update(
            creado_en=ahora,
        )

        response = self.client.get(reverse("tramites:bandeja"), {"modo": "todas"})
        self.assertEqual(response.status_code, 200)
        entradas = list(response.context["entradas"])
        self.assertEqual(entradas[0].notificacion_id, entrada_reciente.notificacion_id)
        self.assertEqual(entradas[1].notificacion_id, entrada_media.notificacion_id)
        self.assertEqual(entradas[2].notificacion_id, entrada_antigua.notificacion_id)

    def test_marcar_notificacion_ajax_responde_json(self):
        destinatario = self._crear_destinatario(indice=1, leido=False)
        response = self.client.post(
            reverse("tramites:bandeja-marcar", args=[destinatario.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"ok": True, "pk": destinatario.pk},
        )
        destinatario.refresh_from_db()
        self.assertTrue(destinatario.leido)
        self.assertIsNotNone(destinatario.leido_en)

    def test_marcar_todo_ajax_responde_json(self):
        for indice in range(3):
            self._crear_destinatario(indice=indice, leido=False)

        response = self.client.post(
            reverse("tramites:bandeja-marcar-todo"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"ok": True})
        self.assertFalse(
            models.BandejaNotificacionDestinatario.objects.filter(
                usuario=self.user,
                leido=False,
            ).exists()
        )
