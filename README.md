# Secundarias Jurídico · Sistema de Trámites

Aplicación Django para registrar y consultar los trámites jurídicos de secundarias. El sistema concentra en una sola vista el alta, filtro y seguimiento de cada trámite, además de incluir una herramienta auxiliar que valida los requisitos de licencias médicas (años de servicio y días efectivos).

---

## 🚀 Módulos disponibles

| Módulo | Descripción | URL |
|--------|-------------|-----|
| **Trámites** | CRUD completo de trámites: captura de CCT, folio inicial, estatus y observaciones. Incluye filtros por CCT, estatus, tipo y rango de fechas. | `/tramites/` |
| **Herramientas** | Centro de utilerías. Incluye el **Analizador de requisitos del trámite** y la **Consulta de plantillas de secundarias**. | `/herramientas/`, `/herramientas/analizador/` y `/herramientas/plantillas-secundarias/` |

---

## 🧱 Arquitectura básica

```
tramites/
├── admin.py          # Configuración del panel de administración
├── api_urls.py       # Endpoints REST (catálogo de CCT)
├── apps.py           # Configuración de la app (app_label histórico: licencias)
├── filters.py        # Filtros de la vista de trámites
├── forms.py          # Formulario con búsqueda asistida de CCT
├── models.py         # Catálogos y modelo CasoInterno (Trámite)
├── static/           # CSS, JS y assets de interfaz
├── templates/        # Base y páginas de trámites/herramientas
├── urls.py           # Rutas HTML
└── views.py          # Vistas protegidas con permisos y mensajes
```

La aplicación mantiene `app_label = "licencias"` para no recrear las tablas existentes; únicamente se simplificó el dominio a **Trámite** y se eliminaron los módulos de Control, Protocolos, KPIs, Importador e Incidencias.

---

## ⚙️ Requisitos previos

- Docker Desktop (recomendado)
- Python 3.11+
- PostgreSQL 13+ (se provee contenedor `cejei_postgres_5532`)
- Virtualenv (`python -m venv .venv`)

---

## 🛠️ Instalación rápida

### Opción recomendada: todo en Docker

```bash
git clone <repo>
cd project_secu_juridi
cp .env.example .env
./scripts/docker_up.sh --initdb   # primera vez (inicializa BD + catálogo CCT)
./scripts/docker_up.sh            # siguientes arranques
```

Sistema disponible en `http://127.0.0.1:8000`.

### Opción alternativa: Django local + PostgreSQL Docker

```bash
git clone <repo>
cd project_secu_juridi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose -f docker/docker-compose.yml up -d postgres
python manage.py migrate --noinput
./scripts/bootstrap_data.sh  # migra e importa cct_secundarias.csv
python manage.py createsuperuser  # opcional
python manage.py runserver 0.0.0.0:8000
```

### Importar catálogo de CCT (requerido la primera vez)

```bash
source .venv/bin/activate
python manage.py import_ccts --path "cct_secundarias.csv"
```

El archivo debe incluir las columnas `CCT`, `c_nombre`, `ASESOR`, `sostenimiento_c_subcontrol` y `tiponivelsub_c_servicion3`.

---

## 🎨 Frontend (Tailwind + CSS legado)

- El CSS histórico vive en `tramites/static/css/` y se mantiene activo.
- Tailwind se compila desde `tramites/static/src/tailwind.css` hacia `tramites/static/css/tailwind.css` (preflight desactivado para convivir con los estilos actuales).
- Comandos:
  ```bash
  npm install               # una vez
  npm run tailwind:watch    # dev: recompila al guardar templates/js
  npm run tailwind:build    # prod: CSS minificado listo para collectstatic
  ```
- Asegúrate de correr `npm run tailwind:build` antes de `python manage.py collectstatic --noinput` en despliegues.

---

## 🧭 Uso del módulo Trámites

1. Inicia sesión y accede a `/tramites/`.
2. Usa el buscador de CCT para precargar los datos del centro de trabajo.
3. Registra:
   - Descripción breve
   - Fecha de apertura
   - Estatus y tipo inicial (catálogos editables en el admin)
   - Folio/asunto del primer oficio (opcional)
4. Desde el listado puedes filtrar por CCT, estatus, tipo, asesor y rango de fechas.
5. Al editar un trámite, cada cambio de estatus queda guardado en el historial.
6. En el formulario encontrarás la sección **Incidencias (opcional)** para capturar nombre del docente, afiliación (IMSS/ISSSTE), fechas y días otorgados. Si eliges ISSSTE se calcula `incidencia_dias_otorgados` con las fechas; si eliges IMSS se calcula `incidencia_fecha_termino` con los días. Todos los campos pueden omitirse y los endpoints aceptan los nuevos atributos `incidencia_*` sin romper compatibilidad.

---

## 🧮 Herramienta “Analizador de requisitos”

Ubicación: `/herramientas/analizador/`

Permite:
- Verificar si el servidor público cumple 15 años de servicio.
- Capturar intervalos de licencias médicas y contabilizar solo los días válidos.
- Cambiar el régimen (ISSSTE/IMSS) para recalcular la meta de días.
- Generar un resumen visual con badges y alertas.

---

## 🔎 Herramienta “Consulta de plantillas de secundarias”

Ubicación: `/herramientas/plantillas-secundarias/`

Permite:
- Buscar empleados por nombre, RFC o CURP.
- Consultar centros de trabajo por CCT o nombre.
- Filtrar por ciclo escolar y validar el último registro disponible.
- Mostrar claves, situación, función y datos de contacto asociados al registro.

Para alimentar esta herramienta importa el CSV de plantillas:

```bash
source .venv/bin/activate
python manage.py import_plantillas --path "REPORTE_PLANTILLA_2014_2025.csv"
```

---

## 🔐 Permisos principales

| Permiso | Uso |
|---------|-----|
| `licencias.view_casointerno` | Acceso al listado y detalles. |
| `licencias.add_casointerno`  | Registrar nuevos trámites. |
| `licencias.change_casointerno` | Editar información y estatus. |
| `licencias.delete_casointerno` | Eliminar trámites. |
| `licencias.add_cctsecundaria`, `change`, `delete` | Crear/editar CCT desde el modal del formulario. |

---

## 📚 Documentos de apoyo

- `LEVANTAR_PROYECTO.md`: checklist para configurar el entorno local.
- `INICIO_RAPIDO.md`: pasos funcionales para el personal jurídico.
- `VERIFICACION_CAMBIOS.md`: **Definition of Done** y pruebas manuales obligatorias antes de liberar.
- `PROMPT_RENOMBRAR_TRAMITES.md`: guía para eliminar rastros del nombre histórico “Licencias” y usar “Trámites”.
- `RENOMBRADO_TRAMITES_PLAN.md`: plan seguro para migrar nombres sin perder datos (app_label histórico y BD).

## ✅ Puerta de entrada (Definition of Done)

- Cada cambio debe pasar los cuatro tests funcionales de `VERIFICACION_CAMBIOS.md` (crear, filtrar, editar trámites y usar el analizador).
- Completa la checklist previa a despliegue de `VERIFICACION_CAMBIOS.md` como criterio de salida.
- Antes de liberar: revisa los logs (`django_server.log`) para descartar errores y confirma que el listado de trámites usa queries optimizadas (ej. `select_related`, <10 queries).

---

## 📞 Soporte rápido

- **¿Cómo lo levanto?** → `LEVANTAR_PROYECTO.md`
- **¿Cómo registro un trámite?** → `/tramites/` (la interfaz guía paso a paso)
- **¿Cómo valido requisitos?** → `/herramientas/analizador/`

---

**Última actualización:** Enero 2025
