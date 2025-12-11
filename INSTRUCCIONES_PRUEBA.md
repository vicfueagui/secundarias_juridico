# INSTRUCCIONES DE PRUEBA: PREFIJO CRUD

## Cambios realizados:

1. ✅ Agregada modal `#prefijo-oficio-modal` a `tramites_detail.html` (línea 406)
2. ✅ Agregado form `#prefijo-oficio-form` con fieldset `#prefijo-oficio-fields`
3. ✅ Mejorado debugging con `window.prefijoCrudDebug` para guardar logs
4. ✅ Agregado logging detallado en cada paso

## Cómo probar:

### Opción 1: Usando tramites_form.html (simplemente para verificación)
1. Ir a `/tramites/caso/crear/`
2. Ver que el campo "Prefijos sugeridos" tiene botones
3. Hacer clic en "Nuevo prefijo"
4. Ver que se abre la modal `prefijo-oficio-modal`
5. Llenar el formulario y guardar
6. Verificar que se agrega a la lista

### Opción 2: Usando tramites_detail.html (LA MÁS IMPORTANTE)
1. Ir a `/tramites/caso/<id>/` (con un ID real de un caso existente)
2. Hacer clic en "Agregar trámite al caso"
3. Se abre modal "tramite-caso-modal"
4. En el campo "Prefijos sugeridos", hacer clic en "Nuevo prefijo"
5. **ESPERADO**: Se abre la modal `prefijo-oficio-modal`
6. Llenar nombre de prefijo y descripción
7. Hacer clic en "Guardar"
8. **ESPERADO**: Se cierra la modal y se agrega el prefijo a la lista de opciones
9. El número de oficio se actualiza automáticamente con el prefijo

## Debugging - Comandos en browser console:

```javascript
// Ver todos los logs de inicialización
window.prefijoCrudDebug.logs

// Ver todos los errores
window.prefijoCrudDebug.errors

// Ver cuántas veces se llamó la función
window.prefijoCrudDebug.calls

// Buscar por un mensaje específico
window.prefijoCrudDebug.logs.filter(log => log.msg.includes("Contexto"))

// Ver el último error
window.prefijoCrudDebug.errors[window.prefijoCrudDebug.errors.length - 1]
```

## Qué verificar:

1. **Logs de inicialización**: 
   - Debería ver "Contexto detectado" con `isDetailView: true`
   - Debería ver "Select encontrado" con ID correcto
   - Debería ver "Modal y form encontrados" con todos `true`
   - Debería ver "Botones encontrados en contenedor" o "Botones seleccionados (estrategia 2)"

2. **Logs de clicks**:
   - Cuando hagas clic en "Nuevo prefijo": debería ver "Click detectado en botón"
   - Cuando haga submit: debería ver logs de creación

3. **Si hay errores**:
   - Verificar `window.prefijoCrudDebug.errors` para ver qué salió mal
   - El error dirá cuál elemento no se encontró

## Estructura esperada en tramites_detail.html:

```
<div class="form-field form-field--full">
  <select id="prefijo-oficio-select-modal">...</select>
  <div class="field-actions">
    <button data-prefijo-oficio-modal-open="">Nuevo prefijo</button>
    ...
  </div>
</div>

<!-- Modal -->
<div class="modal" id="prefijo-oficio-modal">
  <form id="prefijo-oficio-form">
    <fieldset id="prefijo-oficio-fields">
      ...
    </fieldset>
  </form>
</div>
```

Si esta estructura no está presente, la inicialización fallará.

## Archivos modificados:

- `/tramites/templates/tramites/tramites/tramites_detail.html` - Agregada modal
- `/tramites/static/js/app.js` - Mejorado debugging

## Próximos pasos si aún no funciona:

1. Ejecutar comandos de debugging en browser console
2. Revisar `window.prefijoCrudDebug.logs` para ver dónde falla
3. Si hay logs pero los botones no responden: problema con event listeners
4. Si no hay logs: problema con timing/inicialización
