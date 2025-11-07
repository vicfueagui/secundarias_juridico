from __future__ import annotations

from django.apps import AppConfig


class LicenciasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "licencias"
    verbose_name = "Gestión de Licencias (Secundarias)"

    def ready(self) -> None:
        """Registrar señales en cuanto la app está lista."""
        # Import local signals de ser necesario.
        try:
            import licencias.signals  # noqa: F401
        except ImportError:
            # No hay señales definidas todavía.
            pass

