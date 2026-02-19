from __future__ import annotations

from datetime import date
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from tramites import forms, models


class TramiteCasoTrabajadoresTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester_tramite",
            email="tester_tramite@example.com",
            password="password",
            is_staff=True,
        )
        perms = Permission.objects.filter(
            codename__in=[
                "add_tramitecaso",
                "view_casointerno",
            ],
            content_type__app_label="licencias",
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)

        self.cct = models.PlantillaCentroTrabajo.objects.create(
            cct="31ABC0001H",
            nombre="Secundaria Técnica 1",
            asesor="Asesor 1",
            sostenimiento="Federal",
            subnivel="Secundaria",
        )
        self.estatus_caso = models.EstatusCaso.objects.create(nombre="Abierto", orden=1)
        self.tipo_inicial = models.TipoProceso.objects.create(nombre="Licencia")
        self.caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_caso,
            tipo_inicial=self.tipo_inicial,
            asunto="Caso base",
        )

        self.trabajador_base = models.PlantillaEmpleado.objects.create(
            nombre="Trabajador Base",
            rfc="BASE800101AAA",
        )
        self.trabajador_nuevo = models.PlantillaEmpleado.objects.create(
            nombre="Trabajador Nuevo",
            rfc="NUEV800101AAA",
        )
        models.CasoTrabajador.objects.create(
            caso=self.caso,
            trabajador=self.trabajador_base,
            es_principal=True,
        )

    def test_crear_tramite_anexo_permite_editar_centro_sin_modificar_caso_base(self):
        payload = {
            "tramite_caso-cct_codigo": self.cct.cct,
            "tramite_caso-asesor_cct": "Asesor distinto para anexo",
            "tramite_caso-tipo": str(self.tipo_inicial.pk),
            "tramite_caso-tipo_prorroga": "inicial",
            "tramite_caso-fecha": date.today().isoformat(),
            "tramite_caso-asunto": "Trámite anexo con trabajador editado",
            "tramite_caso-trabajador_principal": str(self.trabajador_nuevo.pk),
            "tramite_caso-trabajador_principal_nombre": self.trabajador_nuevo.nombre,
            "tramite_caso-trabajadores_adicionales": "[]",
            "tramite_caso-trabajadores_centros": "{}",
        }

        response = self.client.post(
            reverse("tramites:tramite-caso-create", kwargs={"caso_pk": self.caso.pk}),
            payload,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(models.TramiteCaso.objects.filter(caso=self.caso).count(), 1)
        tramite = models.TramiteCaso.objects.get(caso=self.caso)
        self.assertEqual(tramite.cct_id, self.caso.cct_id)
        self.assertEqual(tramite.asesor_cct, "Asesor distinto para anexo")

        self.caso.refresh_from_db()
        self.assertEqual(self.caso.asesor_cct, "Asesor 1")

        relaciones = list(models.CasoTrabajador.objects.filter(caso=self.caso).order_by("trabajador__nombre"))
        self.assertEqual(len(relaciones), 1)
        self.assertEqual(relaciones[0].trabajador_id, self.trabajador_base.id)
        self.assertTrue(relaciones[0].es_principal)

    def test_crear_tramite_anexo_con_estatus_vacio_no_registra_historial(self):
        payload = {
            "tramite_caso-cct_codigo": self.cct.cct,
            "tramite_caso-asesor_cct": "Asesor sin estatus",
            "tramite_caso-tipo": str(self.tipo_inicial.pk),
            "tramite_caso-estatus": "",
            "tramite_caso-tipo_prorroga": "inicial",
            "tramite_caso-fecha": date.today().isoformat(),
            "tramite_caso-asunto": "Trámite anexo sin estatus",
            "tramite_caso-trabajador_principal": str(self.trabajador_nuevo.pk),
            "tramite_caso-trabajador_principal_nombre": self.trabajador_nuevo.nombre,
            "tramite_caso-trabajadores_adicionales": "[]",
            "tramite_caso-trabajadores_centros": "{}",
        }

        response = self.client.post(
            reverse("tramites:tramite-caso-create", kwargs={"caso_pk": self.caso.pk}),
            payload,
        )

        self.assertEqual(response.status_code, 302)
        tramite = models.TramiteCaso.objects.get(caso=self.caso)
        self.assertIsNone(tramite.estatus_id)
        self.assertFalse(
            models.HistorialEstatusTramiteCaso.objects.filter(tramite=tramite).exists()
        )

    def test_caso_form_persiste_trabajador_manual_en_plantilla_y_caso(self):
        manual_name = "Trabajadora Manual Principal"
        manual_rfc = "MAPR900101AAA"
        payload = {
            "cct_codigo": self.cct.cct,
            "cct_nombre": self.cct.nombre,
            "cct_sistema": self.cct.sostenimiento,
            "cct_modalidad": self.cct.subnivel,
            "asesor_cct": self.cct.asesor,
            "fecha_apertura": date.today().isoformat(),
            "estatus": str(self.estatus_caso.pk),
            "tipo_inicial": str(self.tipo_inicial.pk),
            "tipo_prorroga": "inicial",
            "asunto": "Caso con trabajador manual",
            "numero_oficio": "",
            "trabajador_principal": "",
            "trabajador_principal_nombre": manual_name,
            "trabajadores_adicionales": "[]",
            "trabajadores_centros": "{}",
            "trabajadores_manuales": json.dumps(
                [
                    {
                        "id": "manual:test-principal",
                        "nombre": manual_name,
                        "rfc": manual_rfc,
                        "curp": "",
                        "manual": True,
                    }
                ]
            ),
            "rangos_fechas_adicionales": "[]",
            "centros_trabajo_adicionales": "[]",
            "receptores_adicionales": "[]",
            "generadores_adicionales": "[]",
            "tipos_violencia_adicionales": "[]",
        }
        form = forms.CasoInternoForm(data=payload, instance=self.caso)

        self.assertTrue(form.is_valid(), form.errors)
        caso = form.save()
        form.save_trabajadores(caso)

        trabajador_manual = models.PlantillaEmpleado.objects.get(rfc=manual_rfc)
        relacion = models.CasoTrabajador.objects.get(caso=caso, trabajador=trabajador_manual)

        self.assertTrue(relacion.es_principal)
        self.assertEqual(caso.trabajadores_manuales, [])
