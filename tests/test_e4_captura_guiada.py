from __future__ import annotations

import json
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from tramites import forms, models


class E4CapturaGuiadaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operador_e4",
            email="operador_e4@example.com",
            password="password",
            is_staff=True,
        )
        perms = Permission.objects.filter(
            codename__in=[
                "view_casointerno",
                "add_casointerno",
                "change_casointerno",
                "view_tramitecaso",
                "add_tramitecaso",
                "change_tramitecaso",
            ],
            content_type__app_label="licencias",
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)

        self.cct = models.PlantillaCentroTrabajo.objects.create(
            cct="31E4C0001A",
            nombre="Secundaria E4",
            asesor="Asesor E4",
            sostenimiento="Federal",
            subnivel="General",
        )
        self.tipo_general = models.TipoProceso.objects.create(nombre="Atención jurídica general")
        self.tipo_licencia = models.TipoProceso.objects.create(nombre="Licencia médica")
        self.estatus_caso = models.EstatusCaso.objects.create(nombre="Abierto E4", orden=1)
        self.estatus_tramite = models.EstatusTramite.objects.create(nombre="En seguimiento E4", orden=1)
        self.caso = models.CasoInterno.objects.create(
            cct=self.cct,
            cct_nombre=self.cct.nombre,
            cct_sistema=self.cct.sostenimiento,
            cct_modalidad=self.cct.subnivel,
            asesor_cct=self.cct.asesor,
            fecha_apertura=date.today(),
            estatus=self.estatus_caso,
            tipo_inicial=self.tipo_general,
            asunto="Caso base E4",
            creado_por=self.user,
        )

    def _base_case_payload(self, **overrides):
        payload = {
            "cct": self.cct.cct,
            "cct_codigo": self.cct.cct,
            "cct_nombre": self.cct.nombre,
            "cct_sistema": self.cct.sostenimiento,
            "cct_modalidad": self.cct.subnivel,
            "asesor_cct": self.cct.asesor,
            "fecha_apertura": date.today().isoformat(),
            "estatus": str(self.estatus_caso.pk),
            "tipo_inicial": str(self.tipo_licencia.pk),
            "asunto": "Caso con licencia",
            "tipo_prorroga": "inicial",
            "checklist_documental_payload": json.dumps(
                {
                    "stage": "apertura",
                    "items": [
                        {"key": "solicitud_licencia", "checked": True, "note": ""},
                        {"key": "dictamen_medico", "checked": True, "note": ""},
                    ],
                }
            ),
        }
        payload.update(overrides)
        return payload

    def _base_tramite_payload(self, **overrides):
        payload = {
            "cct_codigo": self.cct.cct,
            "cct_nombre": self.cct.nombre,
            "cct_sistema": self.cct.sostenimiento,
            "cct_modalidad": self.cct.subnivel,
            "asesor_cct": self.cct.asesor,
            "tipo": str(self.tipo_licencia.pk),
            "estatus": str(self.estatus_tramite.pk),
            "fecha": date.today().isoformat(),
            "asunto": "Trámite E4",
            "tipo_prorroga": "inicial",
            "checklist_documental_payload": json.dumps(
                {
                    "stage": "apertura",
                    "items": [
                        {"key": "solicitud_licencia", "checked": True, "note": ""},
                        {"key": "dictamen_medico", "checked": True, "note": ""},
                    ],
                }
            ),
        }
        payload.update(overrides)
        return payload

    def test_case_form_requires_tipo_prorroga_for_licencia(self):
        payload = self._base_case_payload(tipo_prorroga="")
        form = forms.CasoInternoForm(data=payload)
        self.assertFalse(form.is_valid())
        self.assertIn("tipo_prorroga", form.errors)

    def test_case_form_blocks_when_missing_critical_checklist(self):
        payload = self._base_case_payload(
            checklist_documental_payload=json.dumps(
                {
                    "stage": "apertura",
                    "items": [
                        {"key": "solicitud_licencia", "checked": True, "note": ""},
                        {"key": "dictamen_medico", "checked": False, "note": ""},
                    ],
                }
            )
        )
        form = forms.CasoInternoForm(data=payload)
        self.assertFalse(form.is_valid())
        self.assertTrue(any("documentos críticos" in str(msg) for msg in form.non_field_errors()))

    def test_case_form_accepts_complete_critical_checklist(self):
        payload = self._base_case_payload()
        form = forms.CasoInternoForm(data=payload)
        self.assertTrue(form.is_valid(), form.errors)
        checklist = form.cleaned_data.get("checklist_documental") or {}
        self.assertEqual(checklist.get("stage"), "apertura")
        items = checklist.get("items") or []
        self.assertEqual(len(items), 3)

    def test_custom_template_override_marks_field_required(self):
        models.PlantillaCapturaTipo.objects.create(
            tipo_proceso=self.tipo_general,
            ambito=models.PlantillaCapturaTipo.AMBITO_CASO,
            nombre="Plantilla custom E4",
            reglas_campos={
                "default_required_fields": ["numero_oficio"],
            },
            checklist_etapas=[
                {
                    "id": "apertura",
                    "nombre": "Apertura",
                    "documentos": [
                        {"key": "solicitud_firmada", "nombre": "Solicitud firmada", "critico": False},
                    ],
                }
            ],
        )
        payload = self._base_case_payload(
            tipo_inicial=str(self.tipo_general.pk),
            tipo_prorroga="",
            numero_oficio="",
            checklist_documental_payload=json.dumps(
                {
                    "stage": "apertura",
                    "items": [
                        {"key": "solicitud_firmada", "checked": True, "note": ""},
                    ],
                }
            ),
        )
        form = forms.CasoInternoForm(data=payload)
        self.assertFalse(form.is_valid())
        self.assertIn("numero_oficio", form.errors)

    def test_tramite_form_blocks_when_missing_critical_checklist(self):
        payload = self._base_tramite_payload(
            checklist_documental_payload=json.dumps(
                {
                    "stage": "apertura",
                    "items": [
                        {"key": "solicitud_licencia", "checked": False, "note": ""},
                        {"key": "dictamen_medico", "checked": True, "note": ""},
                    ],
                }
            )
        )
        form = forms.TramiteCasoForm(data=payload, caso=self.caso)
        self.assertFalse(form.is_valid())
        self.assertTrue(any("documentos críticos" in str(msg) for msg in form.non_field_errors()))

    def test_views_include_captura_config(self):
        response = self.client.get(reverse("tramites:casointerno-create"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("captura_guiada_config", response.context)
        caso_config = response.context["captura_guiada_config"]
        self.assertIn("templates_by_tipo", caso_config)
        self.assertIn(str(self.tipo_licencia.pk), caso_config["templates_by_tipo"])

        response = self.client.get(
            reverse("tramites:tramite-caso-create", kwargs={"caso_pk": self.caso.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("captura_guiada_config", response.context)
        tramite_config = response.context["captura_guiada_config"]
        self.assertIn(str(self.tipo_licencia.pk), tramite_config["templates_by_tipo"])
