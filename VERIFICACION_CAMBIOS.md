# Verificación de Cambios - Sistema de Trámites

> Esta verificación manual es la **puerta de entrada** para liberar cambios. Es la Definition of Done de cualquier ajuste: todo cambio debe pasar los cuatro tests funcionales (crear, filtrar, editar trámites y usar el analizador), cerrar la checklist y evidenciar revisión de logs y queries optimizadas antes de entregar.

## 🧪 Pruebas Manuales (Definition of Done)

### Test 1: Crear Trámite

**Pasos:**
1. Ir a `/tramites/`
2. Hacer clic en "Nuevo Trámite"
3. Completar formulario:
   - CCT: Seleccionar un CCT válido
   - Descripción: "Trámite de prueba"
   - Fecha de apertura: Hoy
   - Estatus: Seleccionar un estatus
   - Tipo: Seleccionar un tipo
   - Folio/Asunto (opcional): "Folio 001"
4. Guardar

**Resultado esperado:**
- ✅ Trámite se crea correctamente
- ✅ Se asigna un folio automáticamente
- ✅ Aparece en el listado de trámites

### Test 2: Filtrar Trámites

**Pasos:**
1. Ir a `/tramites/`
2. Usar los filtros disponibles:
   - Por CCT
   - Por Estatus
   - Por Tipo
   - Por Asesor
   - Por rango de fechas
3. Verificar que los resultados se filtran correctamente

**Resultado esperado:**
- ✅ Los filtros funcionan correctamente
- ✅ Se muestran solo los trámites que coinciden

### Test 3: Editar Trámite y Cambiar Estatus

**Pasos:**
1. Seleccionar un trámite del listado
2. Hacer clic en "Editar"
3. Cambiar el estatus
4. Guardar

**Resultado esperado:**
- ✅ Cambios se guardan correctamente
- ✅ El historial de cambios se registra
- ✅ Al editar nuevamente, se cargan los nuevos datos

### Test 4: Usar Herramienta Analizador

**Pasos:**
1. Ir a `/herramientas/analizador/`
2. Ingresar datos de servidor público:
   - Fecha de ingreso
   - Régimen (ISSSTE/IMSS)
   - Intervalos de licencia médica
3. Hacer clic en "Analizar"

**Resultado esperado:**
- ✅ Se calcula correctamente si cumple 15 años de servicio
- ✅ Se contabilizan correctamente los días válidos de licencia
- ✅ Se muestra resumen visual con badges y alertas

## 🔧 Verificación de Código

### Verificar estructura del proyecto

```bash
# Verificar que el módulo tramites existe
ls -la /Users/admin/Documents/project_secu_juridi/tramites/

# Resultado esperado:
# admin.py, api_urls.py, apps.py, filters.py, forms.py, models.py, 
# static/, templates/, urls.py, views.py, migrations/
```

### Verificar modelos

```bash
# Verificar que CasoInterno (Trámite) existe
grep -n "class CasoInterno" /Users/admin/Documents/project_secu_juridi/tramites/models.py

# Resultado esperado:
# (Debe encontrar la clase CasoInterno)
```

## 🗄️ Verificación de Base de Datos

### Verificar que los datos se guardan correctamente

```sql
-- Verificar trámites creados
SELECT id, cct_id, descripcion, estatus, tipo, fecha_apertura 
FROM licencias_casointerno 
LIMIT 5;

-- Resultado esperado:
-- id | cct_id | descripcion | estatus | tipo | fecha_apertura
-- 1  | 1      | Trámite de prueba | Abierto | Jurídico | 2025-01-01
```

## 📊 Verificación de Rendimiento

### Verificar queries optimizadas

```bash
# En Django shell
python manage.py shell

# Dentro del shell:
from django.db import connection
from django.test.utils import CaptureQueriesContext
from tramites.views import CasoInternoListView

# Capturar queries
with CaptureQueriesContext(connection) as ctx:
    # Simular vista
    pass

# Verificar que usa select_related
print(f"Total queries: {len(ctx)}")
for query in ctx:
    print(query['sql'])
```

**Resultado esperado:**
- ✅ Menos de 10 queries para cargar listado de trámites
- ✅ Queries optimizadas con `SELECT_RELATED` para relaciones

## 🐛 Verificación de Errores

### Verificar que no hay errores en logs

```bash
# Ver logs de Django
tail -f django_server.log

# Buscar errores
grep -i "error\|exception" django_server.log

# Resultado esperado:
# (No debe haber errores críticos)
```

### Verificar validaciones

```python
# En Django shell
from tramites.models import CasoInterno
from tramites.forms import CasoInternoForm

# Crear formulario con datos válidos
form = CasoInternoForm(data={
    'cct_id': 1,
    'descripcion': 'Prueba',
    'estatus': 1,
    'tipo': 1,
    'fecha_apertura': '2025-01-01',
})

# Verificar que valida correctamente
print(form.is_valid())  # Debe ser True
```

## 📋 Checklist de Verificación

### Antes de Desplegar (obligatoria - Definition of Done)

- [ ] Tailwind compilado (`npm run tailwind:build`) y `tramites/static/css/tailwind.css` actualizado
- [ ] La base de templates carga `{% static 'css/tailwind.css' %}` sin regressiones visuales
- [ ] Test 1: Crear trámite - ✅ PASÓ
- [ ] Test 2: Filtrar trámites - ✅ PASÓ
- [ ] Test 3: Editar trámite y cambiar estatus - ✅ PASÓ
- [ ] Test 4: Usar herramienta analizador - ✅ PASÓ
- [ ] Estructura del proyecto verificada - ✅ VERIFICADO
- [ ] Modelos verificados - ✅ VERIFICADO
- [ ] Base de datos guarda datos correctamente - ✅ VERIFICADO
- [ ] Queries optimizadas - ✅ VERIFICADO
- [ ] No hay errores en logs - ✅ VERIFICADO

### Después de Desplegar

- [ ] Usuarios pueden crear trámites sin errores
- [ ] Filtros funcionan correctamente
- [ ] Cambios de estatus se registran en el historial
- [ ] Herramienta analizador funciona correctamente
- [ ] No hay reportes de errores en producción
- [ ] Rendimiento es aceptable

## 🚀 Despliegue

### Pasos para desplegar

1. **Backup de base de datos:**
   ```bash
   python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json
   ```

2. **Aplicar cambios:**
   ```bash
   git pull origin main
   python manage.py migrate
   ```

3. **Recolectar archivos estáticos:**
   ```bash
   python manage.py collectstatic --noinput
   ```

4. **Reiniciar servidor:**
   ```bash
   python manage.py runserver
   ```

5. **Verificar que funciona:**
   - Acceder a `/tramites/`
   - Crear un trámite de prueba
   - Filtrar trámites
   - Verificar que se cargan los datos

## 📞 Rollback

Si algo falla:

```bash
# Restaurar base de datos
python manage.py loaddata backup_YYYYMMDD_HHMMSS.json

# Revertir cambios de código
git revert <COMMIT_HASH>

# Reiniciar servidor
python manage.py runserver
```

## 📝 Notas

- El sistema mantiene `app_label = "licencias"` para compatibilidad con base de datos existente
- No se requieren migraciones de base de datos para cambios menores
- Los datos existentes se cargan correctamente
- La API REST está disponible en `/api/`

## ✅ Conclusión

Una vez que todos los tests pasen, los cambios están listos para producción.

**Responsable de verificación:** [Tu nombre]
**Fecha de verificación:** [Fecha]
**Resultado:** ✅ APROBADO / ❌ RECHAZADO
