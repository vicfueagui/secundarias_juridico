from __future__ import annotations

from django.apps import AppConfig


class TramitesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tramites"
    label = "licencias"  # Conserva el app_label histórico para las migraciones existentes.
    verbose_name = "Gestión de Trámites"

    def ready(self) -> None:
        """Registrar señales en cuanto la app está lista."""
        # Import local signals de ser necesario.
        try:
            from tramites import signals  # noqa: F401
        except (ImportError, ModuleNotFoundError):
            # No hay señales definidas todavía.
            pass
