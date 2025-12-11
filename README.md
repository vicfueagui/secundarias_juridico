# Secundarias Jurídico · Sistema de Trámites

Aplicación Django para registrar y consultar los trámites jurídicos de secundarias. El sistema concentra en una sola vista el alta, filtro y seguimiento de cada trámite, además de incluir una herramienta auxiliar que valida los requisitos de licencias médicas (años de servicio y días efectivos).

---

## 🚀 Módulos disponibles

| Módulo | Descripción | URL |
|--------|-------------|-----|
| **Trámites** | CRUD completo de trámites: captura de CCT, folio inicial, estatus y observaciones. Incluye filtros por CCT, estatus, tipo y rango de fechas. | `/tramites/` |
| **Herramientas** | Centro de utilerías. Actualmente solo mantiene el **Analizador de requisitos del trámite**, que calcula los días válidos de licencia y verifica los 15 años de servicio. | `/herramientas/` y `/herramientas/analizador/` |

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

- Python 3.11+
- PostgreSQL 13+ (se provee contenedor `cejei_postgres_5532`)
- Virtualenv (`python -m venv .venv`)

---

## 🛠️ Instalación rápida

```bash
git clone <repo>
cd project_secu_juridi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # opcional
python manage.py runserver
```

### Importar catálogo de CCT (requerido la primera vez)

```bash
source .venv/bin/activate
python manage.py import_ccts --path "cct_secundarias.csv"
```

El archivo debe incluir las columnas `CCT`, `c_nombre`, `ASESOR`, `sostenimiento_c_subcontrol` y `tiponivelsub_c_servicion3`.

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

---

## 🧮 Herramienta “Analizador de requisitos”

Ubicación: `/herramientas/analizador/`

Permite:
- Verificar si el servidor público cumple 15 años de servicio.
- Capturar intervalos de licencias médicas y contabilizar solo los días válidos.
- Cambiar el régimen (ISSSTE/IMSS) para recalcular la meta de días.
- Generar un resumen visual con badges y alertas.

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
- `VERIFICACION_CAMBIOS.md`: pruebas recomendadas antes de liberar.

---

## 📞 Soporte rápido

- **¿Cómo lo levanto?** → `LEVANTAR_PROYECTO.md`
- **¿Cómo registro un trámite?** → `/tramites/` (la interfaz guía paso a paso)
- **¿Cómo valido requisitos?** → `/herramientas/analizador/`

---

**Última actualización:** Enero 2025
