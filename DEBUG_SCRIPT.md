# Script de Debugging para Browser Console

Ejecuta estos comandos en la consola del navegador (F12 en Chrome/Firefox):

## 1. Verificar que el select existe
```javascript
document.querySelector("#prefijo-oficio-select-modal")
```
**Esperado**: Retorna el elemento `<select>`
**Si retorna null**: El problema está en que el select no existe

## 2. Verificar que está dentro de .form-field
```javascript
document.querySelector("#prefijo-oficio-select-modal").closest(".form-field")
```
**Esperado**: Retorna el div `.form-field`
**Si retorna null**: La estructura HTML no es la esperada

## 3. Verificar que existe .field-actions
```javascript
document.querySelector("#prefijo-oficio-select-modal").closest(".form-field").querySelector(".field-actions")
```
**Esperado**: Retorna el div `.field-actions`
**Si retorna null**: El selector `.field-actions` no funciona

## 4. Verificar que los botones existen
```javascript
document.querySelector("#prefijo-oficio-select-modal").closest(".form-field").querySelector(".field-actions").querySelectorAll("[data-prefijo-oficio-modal-open]")
```
**Esperado**: Retorna 1 botón
**Si retorna NodeList vacío**: Los botones no tienen el atributo correcto

## 5. Verificar que se llamó initPrefijoOficioCrud()
```javascript
prefijoCrudInitialized
```
**Esperado**: `true` (si se ejecutó correctamente) o `undefined` (si no se ejecutó)
**Si es `undefined`**: La función no se llamó

## 6. Ver todos los logs de la función
```javascript
console.log("Buscar logs que contengan: [initPrefijoOficioCrud]")
```

## 7. Hacer un test manual - Simular click en botón
```javascript
const btn = document.querySelector("[data-prefijo-oficio-modal-open]");
console.log("Botón encontrado:", btn);
btn?.click();
```

## 8. Si el click funciona, ver si la modal se abre
```javascript
document.querySelector("#prefijo-oficio-modal").hidden
```
**Esperado**: `false` (modal abierta)

## Análisis de la salida:
- Si 1-4 todos retornan elementos → El HTML está bien
- Si 5 retorna `true` → La función se ejecutó
- Si 6 muestra logs → Los console.log se están ejecutando
- Si 7 abre la modal → Los event listeners funcionan
- Si alguno falla → Ese es el punto de fallo
