# Pasos para Levantar el Proyecto

## Control de Licencias Niveles Educativos 2025-2030

## 🚀 Configuración Inicial (Primera vez)

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

**Verificar que está corriendo:**
```bash
docker ps | grep cejei
```

Deberías ver:
```
cejei_postgres_5532   Up   0.0.0.0:5532->5432/tcp
```

---

### 3. Levantar el Servidor Django

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

### 4. Acceder al Sistema

### 5. Importar el catálogo de CCT (una sola vez)

Antes de usar el módulo de Control de Internos asegúrate de cargar el archivo `cct_secundarias.csv`:

```bash
source .venv/bin/activate
python manage.py import_ccts --path "cct_secundarias.csv"
```

> Si el archivo se encuentra en otra ruta, ajusta el parámetro `--path`.

El CSV debe incluir los encabezados `CCT`, `c_nombre`, `ASESOR`, `sostenimiento_c_subcontrol` y `tiponivelsub_c_servicion3` (separados por comas y codificados en UTF-8).

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

### Poblar catálogos (si la BD está vacía)
```bash
source .venv/bin/activate && python manage.py poblar_catalogos
```

### Importar CCT y Relación de Protocolos
```bash
source .venv/bin/activate && python manage.py import_protocolos_csv \
  --cct-path "cct_secundarias.csv" \
  --protocolos-path "CONTROL DE PROTOCOLO.csv"
```

> Ajusta las rutas si los archivos CSV se mueven a otra carpeta. El comando carga el catálogo de CCT y los registros históricos en una sola ejecución.

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
- **Configuración:** `cejei_licencias/`
- **App principal:** `licencias/`
- **App de incidencias:** `incidencias/` (captura y reporte de licencias médicas)
- **Templates:** `licencias/templates/`
- **Archivos estáticos:** `licencias/static/`
- **Migraciones:** `licencias/migrations/`
- **Reporteador PDF:** `herramientas/incidencias/` (usa WeasyPrint para exportar)

### Herramienta de incidencias (reporteador)
1. **Migraciones:** `python manage.py migrate incidencias` después de instalar dependencias.
2. **Plantilla base:** configura logo, título y cuerpo en el admin (`Plantillas de reporte de incidencias`).
3. **Captura:** navega a `Herramientas → Relación de licencias médicas` para registrar incidencias.
4. **Edición:** cada incidencia permite editar el cuerpo del reporte antes de descargar el PDF.
5. **Exportar:** el botón "Generar PDF" usa WeasyPrint; si faltan librerías del sistema (Pango, cairo), instálalas según la [documentación oficial](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).

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




1. Detener y eliminar el contenedor existente (si existe)
bash
docker stop cejei_postgres_5532 || true && docker rm cejei_postgres_5532 || true
2. Iniciar el contenedor de PostgreSQL
bash
cd /Users/admin/Documents/project_secu_juridi/docker
docker compose up -d
3. Verificar que el contenedor está en ejecución
bash
docker ps | grep cejei_postgres_5532
4. Verificar la conexión a la base de datos
bash
PGPASSWORD=cejei psql -h 127.0.0.1 -p 5532 -U cejei -d cejei_licencias -c "SELECT 'Conexión exitosa' AS message;"
5. Activar el entorno virtual y ejecutar las migraciones
bash
cd /Users/admin/Documents/project_secu_juridi
source .venv/bin/activate
python manage.py migrate
6. Crear un superusuario (si es la primera vez)
bash
python manage.py createsuperuser
7. Iniciar el servidor de desarrollo
bash
python manage.py runserver
8. Acceder al sistema
URL: http://127.0.0.1:8000
Usuario: admin
Contraseña: (la que hayas configurado al crear el superusuario)
Notas adicionales:
Asegúrate de que el archivo .env esté correctamente configurado con:
POSTGRES_DB=cejei_licencias
POSTGRES_USER=cejei
POSTGRES_PASSWORD=cejei
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5532
Si necesitas importar los datos iniciales, ejecuta:
bash
python manage.py import_ccts --path "cct_secundarias.csv"
