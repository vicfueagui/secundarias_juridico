"""Configuración principal del proyecto Asesores Especializados."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Helpers de entorno
TRUE_VALUES = {"1", "true", "yes", "on"}


def env_bool(var_name: str, default: bool = False) -> bool:
    raw_value = os.environ.get(var_name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in TRUE_VALUES


def env_list(var_name: str, default: list[str]) -> list[str]:
    raw_value = os.environ.get(var_name, "")
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    return values or default


def env_required(var_name: str) -> str:
    value = os.environ.get(var_name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"La variable de entorno {var_name} es obligatoria en producción.")
    return value


DJANGO_ENV = os.environ.get("DJANGO_ENV", "development").strip().lower()
IS_PRODUCTION = DJANGO_ENV in {"production", "prod"}

# Seguridad
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "").strip()
if IS_PRODUCTION and not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY es obligatoria en producción.")
if not SECRET_KEY:
    SECRET_KEY = "django-insecure-dev-only"

DEBUG = env_bool("DJANGO_DEBUG", default=not IS_PRODUCTION)
if IS_PRODUCTION and DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG debe ser false en producción.")

# Dominios permitidos
DEFAULT_ALLOWED_HOSTS = [
    '.ngrok-free.app',  # Cubre cualquier subdominio generado por ngrok
    'ngrok-free.app',
    '127.0.0.1',
    'localhost',
    '192.168.184.175',
    'admins-macbook-pro.local',
]
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS)
if IS_PRODUCTION and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS no puede estar vacío en producción.")

# Configuración para CSRF
CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'http://192.168.184.175:8000',
    'http://admins-macbook-pro.local:8000',
]

# Configuración CORS si usas API REST
CORS_ALLOWED_ORIGINS = [
    'https://*.ngrok-free.app',
    'http://192.168.184.175:8000',
    'http://admins-macbook-pro.local:8000',
]

# Aplicaciones
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "simple_history",
    "tramites.apps.TramitesConfig",
]

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tramites.middleware.RequestUserLoggingMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "asesores_especializados.urls"

# Templates con soporte básico para HTMX
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "tramites" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "tramites.context_processors.bandeja_unread_count",
            ],
        },
    },
]

WSGI_APPLICATION = "asesores_especializados.wsgi.application"
ASGI_APPLICATION = "asesores_especializados.asgi.application"

# Base de datos (PostgreSQL por defecto)
if IS_PRODUCTION:
    db_name = env_required("POSTGRES_DB")
    db_user = env_required("POSTGRES_USER")
    db_password = env_required("POSTGRES_PASSWORD")
    db_host = env_required("POSTGRES_HOST")
    db_port = env_required("POSTGRES_PORT")
else:
    db_name = os.environ.get("POSTGRES_DB", "cejei_licencias")
    db_user = os.environ.get("POSTGRES_USER", "cejei")
    db_password = os.environ.get("POSTGRES_PASSWORD", "cejei")
    db_host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
    db_port = os.environ.get("POSTGRES_PORT", "5432")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": db_name,
        "USER": db_user,
        "PASSWORD": db_password,
        "HOST": db_host,
        "PORT": db_port,
    }
}

# Zona y lenguaje
LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Merida"
USE_I18N = True
USE_TZ = True

# Archivos estáticos y media
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "tramites" / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Logging con usuario y ruta
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_user": {
            "()": "tramites.logging_utils.RequestUserLogFilter",
        },
        "module_name": {
            "()": "tramites.logging_utils.ModuleNameLogFilter",
        },
        "only_info": {
            "()": "tramites.logging_utils.ExactLevelFilter",
            "level_name": "INFO",
        },
        "only_error": {
            "()": "tramites.logging_utils.ExactLevelFilter",
            "level_name": "ERROR",
        },
    },
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} module={module_name} logger={name} user={user} user_id={user_id} ip={client_ip} method={method} status={status_code} duration_ms={duration_ms} request_id={request_id} path={path} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_user", "module_name"],
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "app.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "filters": ["request_user", "module_name"],
            "formatter": "verbose",
        },
        "file_info": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "app-info.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "filters": ["request_user", "module_name", "only_info"],
            "formatter": "verbose",
        },
        "file_error": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "app-error.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "filters": ["request_user", "module_name", "only_error"],
            "formatter": "verbose",
        },
        "file_tramites": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "tramites.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "filters": ["request_user", "module_name"],
            "formatter": "verbose",
        },
        "file_licencias": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "licencias.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "filters": ["request_user", "module_name"],
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console", "file", "file_info", "file_error"],
            "level": "INFO",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console", "file", "file_info", "file_error"],
            "level": "INFO",
            "propagate": False,
        },
        "tramites": {
            "handlers": ["console", "file", "file_tramites", "file_info", "file_error"],
            "level": "INFO",
            "propagate": False,
        },
        "licencias": {
            "handlers": ["console", "file", "file_licencias", "file_info", "file_error"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# DRF + SimpleJWT
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# Internacionalización de fechas
FORMAT_MODULE_PATH = ["tramites.formats"]

# Correo electrónico (Gmail SMTP)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("SMTP_USER", "enlacejuridico.secundarias@gmail.com")
EMAIL_HOST_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Configuraciones varias
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
X_FRAME_OPTIONS = "SAMEORIGIN"
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

LOGIN_REDIRECT_URL = "tramites:casointerno-list"
LOGOUT_REDIRECT_URL = "login"
