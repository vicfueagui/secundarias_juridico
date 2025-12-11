# INSTRUCCIONES PASO A PASO: Corregir CRUD Prefijos

## PASO 1: Debugging Inicial (SIN CAMBIAR CÓDIGO)

Abre el navegador (Chrome, Firefox, etc.) en la página de detalle de un caso:
- URL: `http://localhost:8000/tramites/casos/[ID]/`

Abre Developer Tools (F12 o Cmd+Option+I)

Ve a la pestaña "Console"

Copia y pega esto:

```javascript
// Verificar si la función existe
console.log("initPrefijoOficioCrud existe:", typeof initPrefijoOficioCrud);

// Verificar si ya fue inicializada
console.log("prefijoCrudInitialized:", prefijoCrudInitialized);

// Verificar elementos
console.log("select en detail:", document.querySelector("#prefijo-oficio-select-modal"));
console.log("buttons en detail:", document.querySelectorAll("[data-prefijo-oficio-modal-open]").length);

// Reiniciar y ver logs
prefijoCrudInitialized = false;
initPrefijoOficioCrud();
```

**Si ves logs con valores null o undefined, toma nota de cuál es el que falla.**

---

## PASO 2: Implementar SOLUCIÓN 1 (Recomendada)

**Archivo a modificar**: `/tramites/static/js/app.js`

**Buscar**: La función `initPrefijoOficioCrud()` que empieza alrededor de la línea 2918

**Reemplazar ESTA SECCIÓN**:

```javascript
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
```

**POR ESTA SECCIÓN**:

```javascript
  // 3. Busca los botones - Usando .closest() para mayor robustez
  let openBtn = null, editBtn = null, deleteBtn = null;
  
  if (selectElement) {
    // Buscar el contenedor de field-actions que contiene los botones
    const fieldContainer = selectElement.closest(".form-field");
    const actionsContainer = fieldContainer?.querySelector(".field-actions");
    
    if (actionsContainer) {
      openBtn = actionsContainer.querySelector("[data-prefijo-oficio-modal-open]");
      editBtn = actionsContainer.querySelector("[data-prefijo-oficio-modal-edit]");
      deleteBtn = actionsContainer.querySelector("[data-prefijo-oficio-modal-delete]");
    }
    
    // Fallback si no encuentra en el contenedor directo
    if (!openBtn) {
      const allOpenBtns = document.querySelectorAll("[data-prefijo-oficio-modal-open]");
      openBtn = isDetailView ? allOpenBtns[allOpenBtns.length - 1] : allOpenBtns[0];
    }
    if (!editBtn) {
      const allEditBtns = document.querySelectorAll("[data-prefijo-oficio-modal-edit]");
      editBtn = isDetailView ? allEditBtns[allEditBtns.length - 1] : allEditBtns[0];
    }
    if (!deleteBtn) {
      const allDeleteBtns = document.querySelectorAll("[data-prefijo-oficio-modal-delete]");
      deleteBtn = isDetailView ? allDeleteBtns[allDeleteBtns.length - 1] : allDeleteBtns[0];
    }
  }
```

**Luego**, buscar esta línea de validación:

```javascript
    if (!selectElement || !modal || !form || !numeroInput) {
```

**Y cambiar a**:

```javascript
    if (!selectElement || !modal || !form || !numeroInput || !openBtn) {
```

Esto asegura que si no encuentra los botones, mostrará un error claro.

---

## PASO 3: Mejorar Logging para Debugging

En la misma función `initPrefijoOficioCrud()`, buscar esta línea:

```javascript
    console.log("[initPrefijoOficioCrud] Inicialized successfully", {
```

**Y cambiar el console.log COMPLETO a**:

```javascript
    console.log("[initPrefijoOficioCrud] Inicializado correctamente", {
      isDetailView,
      numeroInputId: numeroInput?.id,
      selectElementId: selectElement?.id,
      fieldContainerId: fieldContainer?.className,
      openBtn: !!openBtn,
      editBtn: !!editBtn,
      deleteBtn: !!deleteBtn,
      timestamp: new Date().toISOString(),
    });
```

Y si ves un warning, agrega más detalles:

```javascript
    console.warn("[initPrefijoOficioCrud] Elementos faltantes", {
      selectElement: !!selectElement,
      selectElementId: selectElement?.id,
      modal: !!modal,
      form: !!form,
      numeroInput: !!numeroInput,
      numeroInputId: numeroInput?.id,
      isDetailView,
      openBtn: !!openBtn,
      editBtn: !!editBtn,
      deleteBtn: !!deleteBtn,
      allOpenBtns: document.querySelectorAll("[data-prefijo-oficio-modal-open]").length,
      timestamp: new Date().toISOString(),
    });
```

---

## PASO 4: Verificar Estructura HTML

Asegúrate que en `tramites_detail.html` (línea ~223-236), la estructura sea:

```html
<div class="form-field form-field--full">
    <label for="prefijo-oficio-select-modal">Prefijos sugeridos</label>
    <select id="prefijo-oficio-select-modal" data-prefijo-oficio-select>
        <!-- opciones -->
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
</div>
```

**SI NO ESTÁ ASÍ**, ajustarlo ahora.

---

## PASO 5: Testear

1. Guarda los cambios
2. Actualiza la página en el navegador (Ctrl+Shift+R para limpiar cache)
3. Abre la consola nuevamente (F12)
4. Navega a un caso
5. Haz clic en "Agregar trámite al caso"
6. Busca logs que digan "[initPrefijoOficioCrud]"
7. Verifica que muestre `openBtn: true`, `editBtn: true`, `deleteBtn: true`
8. Haz clic en "Nuevo prefijo"
9. Debería abrir la modal `prefijo-oficio-modal`

---

## PASO 6: Si Sigue Sin Funcionar

Si después de estos cambios el problema persiste, implementar SOLUCIÓN 2 (Dos funciones separadas):

### Archivo: `/tramites/static/js/app.js`

**Buscar y REEMPLAZAR completamente la función `initPrefijoOficioCrud()`** por esto:

```javascript
  let prefijoFormCrudInitialized = false;
  let prefijoDetailCrudInitialized = false;

  function initPrefijoOficioCrudForm() {
    // SOLO para tramites_form.html
    if (prefijoFormCrudInitialized) return;
    prefijoFormCrudInitialized = true;

    const numeroInput = document.querySelector("#id_numero_oficio");
    if (!numeroInput) return; // No estamos en form view

    const selectElement = document.querySelector("#prefijo-oficio-select");
    const modal = document.getElementById("prefijo-oficio-modal");
    const form = document.getElementById("prefijo-oficio-form");

    if (!selectElement || !modal || !form) {
      console.warn("[initPrefijoOficioCrudForm] Elementos faltantes");
      return;
    }

    // Buscar botones en forma - buscar globalmente
    const openBtn = document.querySelector("[data-prefijo-oficio-modal-open]");
    const editBtn = document.querySelector("[data-prefijo-oficio-modal-edit]");
    const deleteBtn = document.querySelector("[data-prefijo-oficio-modal-delete]");

    if (!openBtn || !editBtn || !deleteBtn) {
      console.warn("[initPrefijoOficioCrudForm] Botones no encontrados");
      return;
    }

    // Resto de la lógica... (copiar desde la función original)
    // openModalForCreate, openModalForEdit, etc.
    
    console.log("[initPrefijoOficioCrudForm] Inicializado correctamente");
  }

  function initPrefijoOficioCrudDetail() {
    // SOLO para tramites_detail.html modal
    if (prefijoDetailCrudInitialized) return;
    prefijoDetailCrudInitialized = true;

    const numeroInput = document.querySelector("#id_tramite_caso-numero_oficio");
    if (!numeroInput) return; // No estamos en detail view

    const selectElement = document.querySelector("#prefijo-oficio-select-modal");
    const modal = document.getElementById("prefijo-oficio-modal");
    const form = document.getElementById("prefijo-oficio-form");

    if (!selectElement || !modal || !form) {
      console.warn("[initPrefijoOficioCrudDetail] Elementos faltantes");
      return;
    }

    // Buscar botones más cerca del select
    const fieldContainer = selectElement.closest(".form-field");
    const actionsContainer = fieldContainer?.querySelector(".field-actions");
    
    const openBtn = actionsContainer?.querySelector("[data-prefijo-oficio-modal-open]");
    const editBtn = actionsContainer?.querySelector("[data-prefijo-oficio-modal-edit]");
    const deleteBtn = actionsContainer?.querySelector("[data-prefijo-oficio-modal-delete]");

    if (!openBtn || !editBtn || !deleteBtn) {
      console.warn("[initPrefijoOficioCrudDetail] Botones no encontrados", {
        fieldContainer: !!fieldContainer,
        actionsContainer: !!actionsContainer,
        openBtn: !!openBtn,
        editBtn: !!editBtn,
        deleteBtn: !!deleteBtn,
      });
      return;
    }

    // Resto de la lógica... (copiar desde la función original)
    
    console.log("[initPrefijoOficioCrudDetail] Inicializado correctamente");
  }

  // Mantener la función original para compatibilidad
  function initPrefijoOficioCrud() {
    initPrefijoOficioCrudForm();
    initPrefijoOficioCrudDetail();
  }
```

**Luego**, cambiar las llamadas:

En `initCasoInternoForm()` (línea ~440):
```javascript
// Cambiar de:
initPrefijoOficioCrud();

// A:
initPrefijoOficioCrudForm();
```

En `initTramiteCasoDetail()` (línea ~2891):
```javascript
// Cambiar de:
initPrefijoOficioCrud();

// A:
initPrefijoOficioCrudDetail();
```

---

## VERIFICACIÓN FINAL

Después de cualquier cambio:

1. Abre los Developer Tools (F12)
2. Ve a Console
3. Sin refrescar, escribe:
```javascript
prefijoFormCrudInitialized
prefijoDetailCrudInitialized
```

4. Debería mostrar valores booleanos
5. Navega a un caso y abre el modal
6. Verifica que diga "[initPrefijoOficioCrudDetail] Inicializado correctamente"
7. Haz clic en "Nuevo prefijo" - debería abrir la modal

---

## NOTAS IMPORTANTES

- **NO cambies la estructura HTML a menos que sea absolutamente necesario**
- **Usa console.log para entender qué está pasando**
- **Si el selector `#prefijo-oficio-select-modal` no existe, verifica tramites_detail.html línea ~225**
- **Si los botones no existen, verifica que tengan los atributos `data-prefijo-oficio-modal-open=""`, etc.**

---

## SI NADA DE ESTO FUNCIONA

1. Toma screenshot de los logs de la consola
2. Verifica en Developer Tools → Elements que la estructura HTML sea correcta
3. Considera si hay otro código JavaScript que esté interfiriendo
4. Ejecuta en la console: `initPrefijoOficioCrudDetail()` manualmente y revisa los logs
