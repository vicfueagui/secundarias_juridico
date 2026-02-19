# Paso 4 - Matriz de Configuración

Fecha: 2026-02-19
Rama: chore/prep-migracion-docker
Fuente: `asesores_especializados/settings.py`

## 1) Variables de entorno usadas por `settings.py`

| Variable | Clasificación | Requerida en producción | Default en desarrollo | Uso principal |
|---|---|---|---|---|
| `DJANGO_ENV` | No secreta | Sí (recomendado) | `development` | Define modo de ejecución (`development`/`production`). |
| `DJANGO_SECRET_KEY` | Secreta | Sí | `django-insecure-dev-only` (solo dev) | Clave criptográfica de Django/JWT signing key. |
| `DJANGO_DEBUG` | No secreta (sensible operativa) | Sí (`false`) | `true` en dev | Activa/desactiva modo debug. |
| `DJANGO_ALLOWED_HOSTS` | No secreta | Sí | Lista local/ngrok por defecto | Control de hosts permitidos. |
| `POSTGRES_DB` | No secreta | Sí | `cejei_licencias` | Nombre de base de datos. |
| `POSTGRES_USER` | No secreta (sensible operativa) | Sí | `cejei` | Usuario de PostgreSQL. |
| `POSTGRES_PASSWORD` | Secreta | Sí | `cejei` (solo dev) | Password de PostgreSQL. |
| `POSTGRES_HOST` | No secreta | Sí | `127.0.0.1` | Host de PostgreSQL. |
| `POSTGRES_PORT` | No secreta | Sí | `5432` | Puerto de PostgreSQL. |
| `SMTP_USER` | No secreta (sensible operativa) | No* | `enlacejuridico.secundarias@gmail.com` | Usuario SMTP (si se habilita backend SMTP). |
| `SMTP_PASSWORD` | Secreta | No* | vacío | Password SMTP (si se habilita backend SMTP). |

\* Actualmente el backend efectivo es consola (`EMAIL_BACKEND = django.core.mail.backends.console.EmailBackend`), por lo que `SMTP_*` no bloquea arranque hoy.

## 2) Clasificación resumida

### Secretas
- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `SMTP_PASSWORD`

### No secretas
- `DJANGO_ENV`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `SMTP_USER`

## 3) Endurecimiento aplicado para producción

Se implementó en `settings.py`:

- Bloqueo de `DEBUG=True` en producción:
  - Si `DJANGO_ENV` es `production/prod` y `DJANGO_DEBUG=true`, el arranque falla con `ImproperlyConfigured`.
- Eliminación de default inseguro de `SECRET_KEY` en producción:
  - `DJANGO_SECRET_KEY` es obligatoria en producción.
  - Solo en desarrollo existe fallback `django-insecure-dev-only`.
- Variables de base de datos obligatorias en producción:
  - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`.
- `ALLOWED_HOSTS` parametrizado:
  - Se usa `DJANGO_ALLOWED_HOSTS` (CSV).
  - En producción no puede quedar vacío.

## 4) Reglas operativas para despliegue

- Desarrollo local:
  - `DJANGO_ENV=development`
  - `DJANGO_DEBUG=true`
- Producción:
  - `DJANGO_ENV=production`
  - `DJANGO_DEBUG=false`
  - `DJANGO_SECRET_KEY` obligatoria y robusta
  - `DJANGO_ALLOWED_HOSTS` con dominios reales
  - `POSTGRES_PASSWORD` robusta (sin defaults)
