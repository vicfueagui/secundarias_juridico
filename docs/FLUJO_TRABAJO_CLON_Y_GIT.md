# Flujo de Trabajo Diario: Clon y Git

Guía simple para trabajar sin enredarte entre:

- la carpeta con Git
- la carpeta que usas para correr el sistema

## 1. Idea base

Piensa así:

- `project_secu_juridi` = carpeta maestra con Git
- `project_secu_juridi_dev` = carpeta operativa para correr y probar

En cristiano:

- en la carpeta maestra editas y versionas
- en la carpeta clon ejecutas y validas

## 2. Regla de oro

No corras archivos Django sueltos como si fueran scripts.

Esto está mal:

```bash
python tramites/forms.py
```

¿Por qué falla?

- `forms.py` no es un programa principal
- depende del paquete `tramites`
- depende de Django y de su configuración
- al ejecutarlo directo, Python no entra por `manage.py`

Por eso viste:

```text
ModuleNotFoundError: No module named 'tramites'
```

## 3. Forma correcta de trabajar

### Para editar código

Usa la carpeta:

```text
/Users/admin/Documents/project_secu_juridi
```

Ahí vive Git.

### Para correr y probar

Usa la carpeta:

```text
/Users/admin/Documents/project_secu_juridi_dev
```

Ahí vive tu clon operativo con Docker.

## 4. Flujo diario recomendado

### Paso 1. Edita en la carpeta con Git

Abre y modifica archivos en:

```text
/Users/admin/Documents/project_secu_juridi
```

### Paso 2. Sincroniza esos cambios al clon

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/dev/sync_to_parallel_clone.sh
```

### Paso 3. Reconstruye lo necesario en el clon

```bash
cd /Users/admin/Documents/project_secu_juridi_dev
docker compose up -d --build web worker nginx
```

### Paso 4. Verifica Django

```bash
cd /Users/admin/Documents/project_secu_juridi_dev
docker compose exec -T web python manage.py check
```

### Paso 5. Prueba en navegador

Abre:

```text
http://127.0.0.1:8081
```

## 5. Cómo inspeccionar formularios, modelos o vistas

No hagas esto:

```bash
python tramites/forms.py
```

Haz esto:

```bash
cd /Users/admin/Documents/project_secu_juridi_dev
docker compose exec -T web python manage.py shell
```

Y ya dentro del shell:

```python
from tramites.forms import CasoInternoForm
```

Eso sí es una forma correcta de cargar un formulario Django.

## 6. Comandos correctos para un principiante

### Ver si el proyecto está sano

```bash
cd /Users/admin/Documents/project_secu_juridi_dev
docker compose exec -T web python manage.py check
```

### Abrir shell de Django

```bash
cd /Users/admin/Documents/project_secu_juridi_dev
docker compose exec -T web python manage.py shell
```

### Ver logs del proyecto

```bash
cd /Users/admin/Documents/project_secu_juridi_dev
docker compose logs --tail=100 web nginx
```

### Ejecutar pruebas

```bash
cd /Users/admin/Documents/project_secu_juridi_dev
docker compose exec -T web pytest
```

## 7. Cuándo haces commit

Los commits se hacen en:

```text
/Users/admin/Documents/project_secu_juridi
```

No en `project_secu_juridi_dev`.

Flujo:

1. editas en `project_secu_juridi`
2. sincronizas al clon
3. pruebas en `project_secu_juridi_dev`
4. si todo está bien, vuelves a `project_secu_juridi`
5. haces `git status`, `git add`, `git commit`

## 8. Tu rutina mínima correcta

```bash
cd /Users/admin/Documents/project_secu_juridi
git status -sb
./scripts/dev/sync_to_parallel_clone.sh

cd /Users/admin/Documents/project_secu_juridi_dev
docker compose up -d --build web worker nginx
docker compose exec -T web python manage.py check
```

## 9. Qué debes evitar

- correr `forms.py`, `models.py` o `views.py` directo
- editar solo en el clon y olvidarte de Git
- hacer cambios grandes sin respaldo previo
- hacer commit sin haber probado en el clon
