# PROMPT DETALLADO: Debug del CRUD de Campo "Prefijos Sugeridos"

## DESCRIPCIÓN DEL PROBLEMA

En la aplicación Django `tramites`, cuando el usuario navega a la vista de detalle de un caso (`tramites_detail.html`) y abre el modal "Agregar trámite al caso", el campo **"Prefijos sugeridos"** tiene un CRUD (Create, Read, Update, Delete) que NO funciona correctamente.

**Síntoma específico**: Los botones "Nuevo prefijo", "Editar seleccionado" y "Eliminar seleccionado" NO responden al hacer clic.

**Contexto importante**: Los otros CRUDs en el mismo modal (tipo-proceso, tipo-violencia, solicitante, destinatario, estatus-tramite) SÍ funcionan correctamente.

## ESTRUCTURA DE LA APLICACIÓN

### Stack Técnico
- **Backend**: Django 4.2.27 + Django REST Framework
- **Frontend**: Vanilla JavaScript (sin frameworks)
- **Base de datos**: PostgreSQL
- **Navegador**: Probado en navegadores modernos

### Rutas Relevantes
```
/Users/admin/Documents/project_secu_juridi/
├── tramites/
│   ├── views.py
│   ├── models.py
│   ├── forms.py
│   ├── serializers.py
│   ├── api_urls.py
│   ├── static/js/app.js
│   └── templates/tramites/tramites/
│       ├── tramites_form.html
│       └── tramites_detail.html
```

### Archivos Críticos
1. **tramites/templates/tramites/tramites/tramites_detail.html** - Vista de detalle
2. **tramites/static/js/app.js** - Lógica JavaScript del CRUD
3. **tramites/views.py** - Vistas Django (CasoInternoDetailView)

## ESTRUCTURA HTML DEL CAMPO PROBLEMÁTICO

### En tramites_detail.html (líneas 215-238)

```html
<!-- Campo 1: Número de oficio -->
<div class="form-field form-field--full">
    <label for="{{ tramite_caso_form.numero_oficio.id_for_label }}">
        {{ tramite_caso_form.numero_oficio.label }}
    </label>
    {{ tramite_caso_form.numero_oficio }}
    <p class="help-text">Opcional. Selecciona un prefijo del catálogo...</p>
</div>

<!-- Campo 2: Prefijos sugeridos - CON PROBLEMA -->
<div class="form-field form-field--full">
    <label for="prefijo-oficio-select-modal">Prefijos sugeridos</label>
    <select id="prefijo-oficio-select-modal" data-prefijo-oficio-select>
        <option value="">Selecciona un prefijo para usarlo o editarlo</option>
        {% for prefijo in prefijos_oficio %}
        <option value="{{ prefijo.id }}">{{ prefijo.nombre }}</option>
        {% endfor %}
    </select>
    <div class="field-actions">
        <button type="button" class="btn btn--ghost btn--sm" data-prefijo-oficio-modal-open="">
            Nuevo prefijo
        </button>
        <button type="button" class="btn btn--ghost btn--sm" data-prefijo-oficio-modal-edit="">
            Editar seleccionado
        </button>
        <button type="button" class="btn btn--danger btn--sm" data-prefijo-oficio-modal-delete="">
            Eliminar seleccionado
        </button>
    </div>
    <p class="help-text">Al seleccionar un prefijo se colocará en el campo de número de oficio...</p>
    <datalist id="prefijo-oficio-options">
        {% for prefijo in prefijos_oficio %}
        <option value="{{ prefijo.nombre }}"></option>
        {% endfor %}
    </datalist>
</div>
```

### En tramites_form.html (línea 111)

```html
<select id="prefijo-oficio-select" data-prefijo-oficio-select="">
    <option value="">Selecciona un prefijo para usarlo o editarlo</option>
    {% for prefijo in prefijos_oficio %}
    <option value="{{ prefijo.nombre }}">{{ prefijo.nombre }}</option>
    {% endfor %}
</select>
```

**DIFERENCIA CRÍTICA**: 
- tramites_form.html usa `value="{{ prefijo.nombre }}"` (string)
- tramites_detail.html usa `value="{{ prefijo.id }}"` (número)

## ESTRUCTURA JAVASCRIPT RELACIONADA

### Función Principal: initPrefijoOficioCrud() - app.js línea ~2918

```javascript
let prefijoCrudInitialized = false;

function initPrefijoOficioCrud() {
  if (prefijoCrudInitialized) return;
  prefijoCrudInitialized = true;

  // 1. Detecta contexto (form vs detail)
  let numeroInput = document.querySelector("#id_numero_oficio");
  const isDetailView = !numeroInput;
  if (!numeroInput) {
    numeroInput = document.querySelector("#id_tramite_caso-numero_oficio");
  }

  // 2. Busca el select
  let selectElement;
  if (isDetailView) {
    selectElement = document.querySelector("#prefijo-oficio-select-modal");
  } else {
    selectElement = document.querySelector("#prefijo-oficio-select");
  }

  // 3. Busca los botones
  const allOpenBtns = document.querySelectorAll("[data-prefijo-oficio-modal-open]");
  const allEditBtns = document.querySelectorAll("[data-prefijo-oficio-modal-edit]");
  const allDeleteBtns = document.querySelectorAll("[data-prefijo-oficio-modal-delete]");
  
  let openBtn = null, editBtn = null, deleteBtn = null;
  
  if (isDetailView && selectElement) {
    openBtn = selectElement.parentElement?.querySelector("[data-prefijo-oficio-modal-open]") || allOpenBtns[allOpenBtns.length - 1];
    editBtn = selectElement.parentElement?.querySelector("[data-prefijo-oficio-modal-edit]") || allEditBtns[allEditBtns.length - 1];
    deleteBtn = selectElement.parentElement?.querySelector("[data-prefijo-oficio-modal-delete]") || allDeleteBtns[allDeleteBtns.length - 1];
  } else {
    openBtn = allOpenBtns[0];
    editBtn = allEditBtns[0];
    deleteBtn = allDeleteBtns[0];
  }

  // 4. Registra event listeners
  if (openBtn) openBtn.addEventListener("click", openModalForCreate);
  if (editBtn) editBtn.addEventListener("click", openModalForEdit);
  if (deleteBtn) deleteBtn.addEventListener("click", openModalForDelete);
  // ... más event listeners
}
```

### Dónde se llama initPrefijoOficioCrud()

1. **En initCasoInternoForm()** (línea ~440) - Para tramites_form.html
2. **En initTramiteCasoDetail()** (línea ~2891) - Para tramites_detail.html

En `initTramiteCasoDetail()` se llama FUERA de la función `initCatalogCruds()` para evitar llamadas múltiples:

```javascript
function initTramiteCasoDetail() {
  const modal = document.getElementById("tramite-caso-modal");
  // ...
  
  const initCatalogCruds = () => {
    initGenericCrud({ ... });
    // ... más CRUDs
  };

  // Inicializar CRUD de Prefijos una sola vez (FUERA de initCatalogCruds)
  initPrefijoOficioCrud();

  openBtn.addEventListener("click", () => {
    resetForm();
    modal.hidden = false;
    initTramiteCasoPrefijos();
    initCatalogCruds();
    const firstInput = modal.querySelector("input, select, textarea");
    firstInput?.focus();
  });
}
```

## MODAL DE PREFIJOS: prefijo-oficio-modal

Ubicado en tramites_form.html y tramites_detail.html:

```html
<div class="modal" id="prefijo-oficio-modal" hidden role="dialog" aria-modal="true">
    <div class="modal-overlay" data-modal-close></div>
    <div class="modal-dialog" role="document">
        <div class="modal-header">
            <h3 class="modal-title" data-modal-title>Agregar prefijo de oficio</h3>
            <button type="button" class="modal-close" data-modal-close aria-label="Cerrar">&times;</button>
        </div>
        <div class="modal-body">
            <form id="prefijo-oficio-form" class="modal-form">
                <fieldset id="prefijo-oficio-fields">
                    <div class="modal-field">
                        <label for="prefijo-oficio-nombre">Prefijo</label>
                        <input type="text" id="prefijo-oficio-nombre" name="nombre" required ...>
                    </div>
                    <!-- más campos -->
                </fieldset>
                <div class="modal-message" data-modal-message role="alert"></div>
                <div class="modal-actions">
                    <button type="submit" class="btn btn--primary btn--md" data-prefijo-oficio-save>
                        Guardar
                    </button>
                    <button type="button" class="btn btn--secondary btn--md" data-modal-close>
                        Cancelar
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
```

## CONTEXTO DJANGO: CasoInternoDetailView

**Archivo**: tramites/views.py línea ~212

```python
class CasoInternoDetailView(
    CasoInternoFormMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView
):
    permission_required = "licencias.view_casointerno"
    model = models.CasoInterno
    template_name = "tramites/tramites/tramites_detail.html"
    context_object_name = "caso"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["historial_estatus"] = self.object.historial_estatus.select_related(...)
        ctx["tramites_caso"] = self.object.tramites_relacionados.select_related(...)
        ctx["tramite_caso_form"] = forms.TramiteCasoForm()
        return ctx
```

**Nota**: CasoInternoFormMixin hereda de CCTCatalogContextMixin que proporciona:
- `prefijos_oficio` (lista de PrefijoOficio activos)
- `prefijos_oficio_api_url` (URL de la API)
- Otros catálogos

## API REST ENDPOINT

**URL**: `/api/prefijos-oficio/`

**ViewSet**: PrefijoOficioViewSet (registrado en api_urls.py)

**Serializer**: PrefijoOficioSerializer

**Métodos disponibles**:
- GET (list)
- POST (create)
- PATCH (update)
- DELETE (destroy)

## DEBUGGING REQUERIDO

### 1. Verificar en Console del Navegador

Cuando el usuario abre el modal y hace clic en "Nuevo prefijo", buscar:

```javascript
// Buscar logs de inicialización
console.log messages que digan "[initPrefijoOficioCrud]"

// Verificar que los elementos existan
document.querySelector("#prefijo-oficio-select-modal") // debería encontrarlo
document.querySelector("#prefijo-oficio-modal") // debería encontrarlo
document.querySelectorAll("[data-prefijo-oficio-modal-open]") // debería haber mínimo 1
```

### 2. Verificar estructura del DOM

```javascript
// En tramites_detail.html, verificar el orden:
const select = document.querySelector("#prefijo-oficio-select-modal");
const parent = select.parentElement;
const buttons = parent.querySelectorAll("[data-prefijo-oficio-modal-open]");
console.log("Encontrados", buttons.length, "botones cerca del select");
```

### 3. Verificar Event Listeners

```javascript
// Después de que se carque la página:
const openBtn = document.querySelector("[data-prefijo-oficio-modal-open]");
console.log("Botón encontrado:", !!openBtn);
console.log("Botón tiene listeners:", openBtn?._getEventListeners?.("click")); // Si el navegador lo permite
```

### 4. Forzar la ejecución

En la console, ejecutar:
```javascript
prefijoCrudInitialized = false; // Resetear la bandera
initPrefijoOficioCrud(); // Llamar de nuevo
```

## HIPÓTESIS DEL PROBLEMA

### Hipótesis 1: Los botones NO se encuentran correctamente
- La búsqueda de botones falla porque `selectElement.parentElement?.querySelector(...)` no retorna los botones
- Solución: Cambiar a una búsqueda más confiable

### Hipótesis 2: Event listeners no se registran
- `openBtn`, `editBtn`, `deleteBtn` son `null` porque no se encuentran
- Los `if (openBtn)` previenen la ejecución silenciosa
- Solución: Mejorar el log para ver qué sucede exactamente

### Hipótesis 3: Contexto incorrecto al inicializar
- `isDetailView` se detecta incorrectamente
- La búsqueda de selectElement falla
- Solución: Revisar la lógica de detección de contexto

### Hipótesis 4: Conflicto con tramites_form.html
- Si el usuario llega a tramites_form.html primero, se inicializa `initPrefijoOficioCrud()`
- Cuando va a tramites_detail.html, la bandera `prefijoCrudInitialized` impide re-inicialización
- El `selectElement` y botones buscados apuntan a los de tramites_form.html, no detail
- Solución: Usar una bandera por contexto, no global

## PASOS PARA CORREGIR

1. **Investigar**: Revisar console.log en navegador cuando se abre modal en tramites_detail.html
2. **Confirmar**: Verificar que `selectElement` y `openBtn` se encuentran correctamente
3. **Revisar lógica**: La búsqueda de botones con `selectElement.parentElement?.querySelector()` es confiable?
4. **Alternativa**: Usar selectores más específicos que no dependan de estructura DOM
5. **Separar contextos**: Posiblemente necesite dos funciones separadas (una para form, otra para detail)
6. **Testing**: Verificar en ambos contextos (tramites_form.html y tramites_detail.html)

## ARCHIVOS A MODIFICAR

- `/Users/admin/Documents/project_secu_juridi/tramites/static/js/app.js` - Función initPrefijoOficioCrud() (línea ~2918)
- Posiblemente: `/Users/admin/Documents/project_secu_juridi/tramites/templates/tramites/tramites/tramites_detail.html` - Si requiere cambios estructurales

## INFORMACIÓN ADICIONAL

### Selectors usando en otros CRUDs que SÍ funcionan:
- Usan `initGenericCrud({ catalogType, selectSelector, modalId, apiEndpoint, fieldConfig })`
- No tienen la complejidad del CRUD de prefijos
- No tienen lógica especial de "aplicar valor al campo de número de oficio"
- Son más simples y reutilizables

### Nota Final
El CRUD de prefijos es el ÚNICO que tiene lógica diferente:
1. Integración con campo "número_oficio" (otros CRUDs no tienen esto)
2. Uso de datalist (otros no)
3. Inicialización manual (otros usan función genérica)
4. Búsqueda compleja de botones (otros no necesitan esto)

Esto sugiere que el problema podría estar en la complejidad de la búsqueda de elementos, no en la lógica del CRUD en sí.
