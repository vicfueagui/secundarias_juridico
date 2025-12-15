# Pasos para Levantar el Proyecto

## Sistema de Trámites Jurídicos - Secundarias

## 🚀 Configuración Inicial (Primera vez)

- Requisitos: Python 3.11+, PostgreSQL 14+ (contenedor `cejei_postgres_5532` en puerto 5532).
- Entorno: virtualenv en `.venv`.

### 0. Instalar Dependencias

**Si es la primera vez que levantas el proyecto:**

```bash
cd /Users/admin/Documents/project_secu_juridi
source .venv/bin/activate
pip install -r requirements.txt
```

**Verificar instalación:**
```bash
python manage.py --version
```

---

### 1. Configurar variables de entorno (.env)

1. Copia el archivo de ejemplo y crea tu configuración local:
   ```bash
   cp .env.example .env
   ```
2. Edita `.env` y ajusta los valores reales. Para el entorno con Docker incluido en este proyecto:
   ```
   POSTGRES_DB=cejei_licencias
   POSTGRES_USER=cejei
   POSTGRES_PASSWORD=cejei
   POSTGRES_HOST=127.0.0.1
   POSTGRES_PORT=5532
   DJANGO_SECRET_KEY=cambia_esta_llave
   DJANGO_DEBUG=true
   ```
   > Usa una `DJANGO_SECRET_KEY` fuerte al desplegar en producción.

3. A partir de ahora no necesitas exportar variables manualmente: `manage.py`, `asgi.py` y `wsgi.py` cargarán automáticamente el `.env`.

---

### 2. Iniciar PostgreSQL (Docker)

```bash
docker start cejei_postgres_5532
```

cd /Users/admin/Documents/project_secu_juridi
docker-compose -f docker/docker-compose.yml up -d postgres


**Verificar que está corriendo:**
```bash
docker ps | grep cejei
```

Deberías ver:
```
cejei_postgres_5532   Up   0.0.0.0:5532->5432/tcp
```

---

### 3. Cargar datos base (migraciones + catálogo CCT)

Ejecuta el bootstrap de datos para desarrollo/QA. Por defecto usa `cct_secundarias.csv` en la raíz del proyecto; puedes pasar otra ruta como primer argumento.

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/bootstrap_data.sh  # o ./scripts/bootstrap_data.sh /ruta/a/cct_secundarias.csv
```

Esto aplicará migraciones y ejecutará `python manage.py import_ccts`.

---

### 4. Levantar el Servidor Django

```bash
cd /Users/admin/Documents/project_secu_juridi
source .venv/bin/activate
python manage.py runserver
```

**O en una sola línea:**
```bash
source .venv/bin/activate && python manage.py runserver
python manage.py runserver 0.0.0.0:8000
```

---

### 5. Acceder al Sistema

- **URL:** http://127.0.0.1:8000
- **Usuario:** admin
- **Contraseña:** admin123

---

## Comandos Útiles

### Verificar puertos en uso
```bash
lsof -ti:8000        # Verificar puerto Django
lsof -ti:5532        # Verificar puerto PostgreSQL
```

### Detener el servidor Django
```bash
lsof -ti:8000 | xargs kill -9
```

### Detener PostgreSQL
```bash
docker stop cejei_postgres_5532
```

### Ver logs del contenedor PostgreSQL
```bash
docker logs cejei_postgres_5532
```

### Verificar estado de la base de datos y permisos
```bash
source .venv/bin/activate && python manage.py check
```

**Este comando verifica:**
- ✅ Conexión a la base de datos
- ✅ Configuración del proyecto
- ✅ Permisos de usuario para crear/editar/eliminar

**Si hay errores de permisos, verificar:**
```bash
# Conectar a PostgreSQL y verificar permisos
docker exec -it cejei_postgres_5532 psql -U cejei -d cejei_licencias -c "\du"
```

### Aplicar migraciones (si es necesario)
```bash
source .venv/bin/activate && python manage.py migrate
```

**Verificar migraciones aplicadas:**
```bash
source .venv/bin/activate && python manage.py showmigrations
```

### Importar catálogo de CCT
```bash
source .venv/bin/activate && python manage.py import_ccts --path "cct_secundarias.csv"
```

> Ajusta la ruta si el archivo CSV se mueve a otra carpeta. El comando actualiza o crea los CCT requeridos por el módulo de trámites.

### Crear superusuario (si es necesario)
```bash
source .venv/bin/activate && python manage.py createsuperuser
```

---

## Información del Proyecto

### Puertos
- **Django:** 8000
- **PostgreSQL:** 5532 (mapeado desde 5432 interno del contenedor)

### Base de Datos
- **Nombre:** cejei_licencias
- **Usuario:** cejei
- **Contraseña:** cejei
- **Host:** 127.0.0.1
- **Puerto:** 5532 (configura `POSTGRES_PORT` en tu `.env`)

### Estructura del Proyecto
- **Configuración:** `asesores_especializados/`
- **App principal:** `tramites/`
- **Templates:** `tramites/templates/`
- **Archivos estáticos:** `tramites/static/`
- **Migraciones:** `tramites/migrations/`
- **Comandos relevantes:** `import_ccts` para poblar el catálogo de CCT

---

## Solución de Problemas

### Error: "That port is already in use"
```bash
lsof -ti:8000 | xargs kill -9
```

### Error: "could not connect to server"
1. Verificar que PostgreSQL está corriendo:
   ```bash
   docker ps | grep cejei
   ```
2. Si no está corriendo, iniciarlo:
   ```bash
   docker start cejei_postgres_5532
   ```

### Error: "No module named 'django'"
Asegúrate de activar el entorno virtual e instalar dependencias:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Error de permisos en la base de datos
Si `python manage.py check` muestra errores de permisos:

1. **Verificar usuario de PostgreSQL:**
   ```bash
   docker exec -it cejei_postgres_5532 psql -U cejei -d cejei_licencias -c "\du"
   ```

2. **Otorgar permisos completos al usuario:**
```bash
docker exec -it cejei_postgres_5532 psql -U cejei -d cejei_licencias -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cejei;"
docker exec -it cejei_postgres_5532 psql -U cejei -d cejei_licencias -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cejei;"
```

3. **Verificar nuevamente:**
```bash
source .venv/bin/activate && python manage.py check
```

---

## Notas Importantes

- **Siempre** exportar `POSTGRES_PORT=5532` antes de ejecutar comandos de Django
- El proyecto usa PostgreSQL en Docker en el puerto **5532** (no 5432)
- Hay otros proyectos usando PostgreSQL en el puerto 5432
- El entorno virtual está en `.venv/`
- Los datos de CCT deben importarse una sola vez con `import_ccts`
