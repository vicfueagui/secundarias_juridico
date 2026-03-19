# Flujo de Tres Entornos

Guía práctica para trabajar con:

- `project_secu_juridi`
- `project_secu_juridi_lab`
- `project_secu_juridi_dev`

## 0. Estado actual recomendado

Hoy la separación correcta quedó así:

- `project_secu_juridi`: repo maestro con Git y GitHub
- `project_secu_juridi_lab`: laboratorio para pruebas antes de publicar
- `project_secu_juridi_dev`: entorno estable para uso más cuidado

Verificación rápida:

```bash
cd /Users/admin/Documents/project_secu_juridi
git status -sb

cd /Users/admin/Documents/project_secu_juridi_lab
docker compose ps

cd /Users/admin/Documents/project_secu_juridi_dev
docker compose ps
```

Si `lab` o `dev` están apagados, no es un desastre. Solo significa que debes levantarlos antes de usarlos.

## 1. Qué es cada carpeta

### `project_secu_juridi`

Es tu carpeta maestra.

Aquí haces:

- edición de código
- `git status`
- `git add`
- `git commit`
- `git push`

Piensa en ella como tu **fuente de verdad**.

### `project_secu_juridi_lab`

Es tu laboratorio.

Aquí haces:

- pruebas de cambios
- reconstrucción de servicios
- validación antes de publicar

Piensa en ella como tu **zona segura de experimentos**.

Puertos actuales:

- URL principal: `http://127.0.0.1:8082`
- URL compatibilidad: `http://127.0.0.1:8002`
- PostgreSQL: `127.0.0.1:5543`

### `project_secu_juridi_dev`

Es tu entorno estable.

Aquí haces:

- respaldo antes de publicar
- actualización solo cuando lo probado en `lab` ya quedó bien
- verificación final del entorno que usarán otros

Piensa en ella como tu **entorno confiable**.

Puertos actuales:

- URL principal: `http://127.0.0.1:8081`
- URL compatibilidad: `http://127.0.0.1:8001`
- PostgreSQL: `127.0.0.1:5542`

## 2. Regla más importante

No mezcles roles.

En cristiano:

- no desarrolles directamente en `dev`
- no hagas commits en `lab`
- no edites en `lab` y luego olvides pasar esos cambios al repo maestro

## 3. Flujo correcto de trabajo

### Etapa A. Cambias código

Siempre empiezas en:

```text
/Users/admin/Documents/project_secu_juridi
```

Ahí modificas archivos.

### Etapa B. Mandas esos cambios a laboratorio

```bash
cd /Users/admin/Documents/project_secu_juridi
make sync-lab
```

Luego reconstruyes `lab`:

```bash
cd /Users/admin/Documents/project_secu_juridi
make rebuild-lab
make check-lab
```

Después pruebas en navegador:

```text
http://127.0.0.1:8082
```

Nota importante:

- `sync-lab` copia el estado actual del repo maestro hacia `lab`
- si tu repo maestro tiene cambios locales sin commit, `lab` también recibirá esos cambios
- eso está bien para probar, pero debes hacerlo con intención

### Etapa C. Si todo sale bien, versionas

Vuelves al repo maestro:

```bash
cd /Users/admin/Documents/project_secu_juridi
git status -sb
git add .
git commit -m "mensaje claro"
git push
```

### Etapa D. Respaldas el entorno estable

Antes de tocar `dev`:

```bash
cd /Users/admin/Documents/project_secu_juridi_dev
PATH="/usr/local/bin:$PATH" ./scripts/backups/backup_full.sh --verify
```

### Etapa E. Publicas a `dev`

Sincronizas el código validado hacia el entorno estable:

```bash
cd /Users/admin/Documents/project_secu_juridi
make sync-dev
make rebuild-dev
make check-dev
```

Después revisas:

```text
http://127.0.0.1:8081
```

## 4. Flujo mínimo diario

Si quieres memorizarlo fácil:

1. editas en `project_secu_juridi`
2. pruebas en `project_secu_juridi_lab`
3. si pasa, haces commit y push
4. respaldas `project_secu_juridi_dev`
5. publicas a `project_secu_juridi_dev`

## 5. Qué nunca debes hacer

- correr `forms.py` o `views.py` directo
- editar primero en `lab`
- editar primero en `dev`
- hacer commit sin haber probado en `lab`
- publicar en `dev` sin respaldo previo

## 6. Comandos que más vas a usar

### Ver cambios en tu repo maestro

```bash
cd /Users/admin/Documents/project_secu_juridi
git status -sb
```

### Sincronizar a laboratorio

```bash
cd /Users/admin/Documents/project_secu_juridi
make sync-lab
make rebuild-lab
make check-lab
```

### Sincronizar a estable

```bash
cd /Users/admin/Documents/project_secu_juridi
make sync-dev
make rebuild-dev
make check-dev
```

### Respaldar estable antes de publicar

```bash
cd /Users/admin/Documents/project_secu_juridi_dev
PATH="/usr/local/bin:$PATH" ./scripts/backups/backup_full.sh --verify
```

### Crear o rehacer laboratorio desde el estable

Usa esto solo cuando quieras reconstruir `lab` desde un respaldo reciente de `dev`:

```bash
cd /Users/admin/Documents/project_secu_juridi
make prepare-lab
```

En cristiano:

- primero respaldas `dev`
- luego rehaces `lab` con esa base de datos y media
- después sincronizas a `lab` el código que quieres probar

## 7. Qué significa “sincronizar”

No significa “hacer git push”.

Aquí significa:

- copiar el código del repo maestro al entorno que corre
- reconstruir servicios si hace falta
- verificar que Django siga sano

Git y sincronización no son lo mismo.

## 8. Tu mapa mental final

Piensa así:

- `project_secu_juridi` = donde escribes y versionas
- `project_secu_juridi_lab` = donde rompes y pruebas
- `project_secu_juridi_dev` = donde publicas con cuidado

## 9. Primera rutina para un principiante

Si mañana empiezas cambios nuevos, haz esto:

1. revisa tu repo maestro con `git status -sb`
2. edita código solo en `project_secu_juridi`
3. manda esos cambios a `lab` con `make sync-lab`
4. reconstruye `lab` con `make rebuild-lab`
5. valida `lab` con `make check-lab`
6. prueba en navegador en `http://127.0.0.1:8082`
7. si todo salió bien, haz `git add`, `git commit` y `git push`
8. respalda `dev`
9. publica a `dev` con `make sync-dev`, `make rebuild-dev` y `make check-dev`
