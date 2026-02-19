# Pasos para Levantar el Proyecto

## Sistema de Trámites Jurídicos - Secundarias

## Flujo recomendado (todo en Docker)

### 1. Preparar variables de entorno

```bash
cd /Users/admin/Documents/project_secu_juridi
cp .env.example .env
```

Valores base recomendados en `.env`:

```env
POSTGRES_DB=cejei_licencias
POSTGRES_USER=cejei
POSTGRES_PASSWORD=cejei
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5532
DJANGO_SECRET_KEY=cambia_esta_llave
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

### 2. Inicializar base de datos (primera vez)

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/docker_up.sh --initdb
```

Esto hace:
- Levanta PostgreSQL.
- Ejecuta migraciones.
- Importa catálogo de CCT desde `cct_secundarias.csv`.
- Levanta Django en el puerto `8000`.

### 3. Arranque normal (siguientes veces)

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/docker_up.sh
```

### 4. Acceso al sistema

- URL: `http://127.0.0.1:8000`
- PostgreSQL expuesto en host: `127.0.0.1:5532`

## Comandos útiles Docker

### Estado de servicios

```bash
docker compose -f docker/docker-compose.yml ps
```

### Ver logs de Django

```bash
docker compose -f docker/docker-compose.yml logs -f web
```

### Reiniciar servicios

```bash
docker compose -f docker/docker-compose.yml restart postgres web
```

### Detener servicios

```bash
docker compose -f docker/docker-compose.yml down
```

### Inicializar BD manualmente (si no te aparece la opción)

```bash
docker compose -f docker/docker-compose.yml run --rm initdb
```

## Solución rápida cuando hubo apagado brusco

1. Abre Docker Desktop y espera a que diga que Docker Engine está activo.
2. Relevanta servicios:
   ```bash
   docker compose -f docker/docker-compose.yml up -d --build postgres web
   ```
3. Si falta inicialización de BD:
   ```bash
   docker compose -f docker/docker-compose.yml run --rm initdb
   ```
4. Verifica estado:
   ```bash
   docker compose -f docker/docker-compose.yml ps
   ```

## Recuperación de emergencia de PostgreSQL (destructivo)

Solo si la base quedó corrupta y aceptas perder datos locales:

```bash
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d postgres
docker compose -f docker/docker-compose.yml run --rm initdb
docker compose -f docker/docker-compose.yml up -d web
```

## Flujo alterno sin Docker para Django (solo referencia)

Si quieres correr Django local y solo PostgreSQL en Docker:

```bash
cd /Users/admin/Documents/project_secu_juridi
docker compose -f docker/docker-compose.yml up -d postgres
source .venv/bin/activate
python manage.py migrate --noinput
python manage.py runserver 0.0.0.0:8000
```
