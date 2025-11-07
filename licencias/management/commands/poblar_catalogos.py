"""Comando para poblar los catálogos iniciales del sistema."""
from django.core.management.base import BaseCommand
from licencias.models import (
    Subsistema, TipoTramite, Etapa, Sindicato, Diagnostico, Area, Resultado
)


class Command(BaseCommand):
    help = "Pobla los catálogos con datos iniciales"

    def handle(self, *args, **options):
        self.stdout.write("Poblando catálogos...")

        # Subsistemas
        subsistemas = [
            {"nombre": "Federal", "descripcion": "Subsistema Federal"},
            {"nombre": "Estatal", "descripcion": "Subsistema Estatal"},
        ]
        for data in subsistemas:
            Subsistema.objects.get_or_create(nombre=data["nombre"], defaults=data)
        self.stdout.write(self.style.SUCCESS(f"✓ {len(subsistemas)} Subsistemas"))

        # Tipos de Trámite
        tipos_tramite = [
            {"nombre": "Licencia 754", "descripcion": "Licencia tipo 754"},
            {"nombre": "70 BIS", "descripcion": "Licencia 70 BIS"},
            {"nombre": "Cambio de Función", "descripcion": "Trámite de cambio de función"},
            {"nombre": "Cambio de actividad", "descripcion": "Trámite de cambio de actividad"},
            {"nombre": "Otro", "descripcion": "Otro tipo de trámite"},
        ]
        for data in tipos_tramite:
            TipoTramite.objects.get_or_create(nombre=data["nombre"], defaults=data)
        self.stdout.write(self.style.SUCCESS(f"✓ {len(tipos_tramite)} Tipos de Trámite"))

        # Sindicatos
        sindicatos = [
            {"nombre": "SYTTE", "descripcion": "Sindicato SYTTE"},
            {"nombre": "SNTE sección 33", "descripcion": "SNTE sección 33"},
            {"nombre": "SNTE sección 57", "descripcion": "SNTE sección 57"},
            {"nombre": "SETEY", "descripcion": "Sindicato SETEY"},
            {"nombre": "GNTE", "descripcion": "Sindicato GNTE"},
        ]
        for data in sindicatos:
            Sindicato.objects.get_or_create(nombre=data["nombre"], defaults=data)
        self.stdout.write(self.style.SUCCESS(f"✓ {len(sindicatos)} Sindicatos"))

        # Diagnósticos (ejemplos)
        diagnosticos = [
            {"nombre": "Enfermedad crónica", "descripcion": "Enfermedad crónica"},
            {"nombre": "Incapacidad temporal", "descripcion": "Incapacidad temporal"},
            {"nombre": "Maternidad", "descripcion": "Licencia por maternidad"},
            {"nombre": "Cuidado familiar", "descripcion": "Cuidado de familiar"},
            {"nombre": "Otro", "descripcion": "Otro diagnóstico"},
        ]
        for data in diagnosticos:
            Diagnostico.objects.get_or_create(nombre=data["nombre"], defaults=data)
        self.stdout.write(self.style.SUCCESS(f"✓ {len(diagnosticos)} Diagnósticos"))

        # Etapas
        etapas = [
            {"nombre": "Recepción", "orden": 1, "es_final": False},
            {"nombre": "En revisión", "orden": 2, "es_final": False},
            {"nombre": "Pendiente de documentación", "orden": 3, "es_final": False},
            {"nombre": "En dictamen", "orden": 4, "es_final": False},
            {"nombre": "Autorizado", "orden": 5, "es_final": True},
            {"nombre": "Rechazado", "orden": 6, "es_final": True},
        ]
        for data in etapas:
            Etapa.objects.get_or_create(nombre=data["nombre"], defaults=data)
        self.stdout.write(self.style.SUCCESS(f"✓ {len(etapas)} Etapas"))

        # Áreas
        areas = [
            {"nombre": "Subsecretaría", "descripcion": "Subsecretaría"},
            {"nombre": "Subd. de Org. y Adm. de Personal -DAF", "descripcion": "Subdirección de Organización y Administración de Personal"},
            {"nombre": "Nivel Educativo", "descripcion": "Nivel Educativo"},
        ]
        for data in areas:
            Area.objects.get_or_create(nombre=data["nombre"], defaults=data)
        self.stdout.write(self.style.SUCCESS(f"✓ {len(areas)} Áreas"))

        # Resultados
        resultados = [
            {"nombre": "Autorizado", "descripcion": "Trámite autorizado"},
            {"nombre": "Rechazado", "descripcion": "Trámite rechazado"},
            {"nombre": "En proceso", "descripcion": "Trámite en proceso"},
            {"nombre": "Pendiente", "descripcion": "Trámite pendiente"},
        ]
        for data in resultados:
            Resultado.objects.get_or_create(nombre=data["nombre"], defaults=data)
        self.stdout.write(self.style.SUCCESS(f"✓ {len(resultados)} Resultados"))

        self.stdout.write(self.style.SUCCESS("\n✅ Catálogos poblados exitosamente"))
