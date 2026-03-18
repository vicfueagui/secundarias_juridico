# Kanban Personal de Blindaje Operativo

Tablero personal para repetir el blindaje operativo de `project_secu_juridi` sin improvisar.

Úsalo antes de:

- tocar lógica sensible
- cambiar infraestructura local
- preparar una evolución en carpeta paralela
- dejar un punto de restauración antes de una mejora grande

## 1. Regla de operación

Orden obligatorio:

1. proteger
2. verificar
3. clonar o restaurar
4. documentar
5. recién entonces evolucionar

No muevas una tarjeta a `Hecho` si no dejaste evidencia concreta: ruta de respaldo, reporte de verificación, ruta del clon o hash de commit/tag.

## 2. Cómo usar este tablero

1. Duplica este archivo o crea una copia con fecha, por ejemplo:
   `docs/KANBAN_BLINDAJE_2026-03-18.md`
2. Mueve cada tarjeta entre columnas.
3. Anota abajo de cada tarjeta la evidencia real.
4. Si algo falla, pasa la tarjeta a `Bloqueado` con el motivo exacto.

## 3. Tablero Base

### Backlog

- [ ] `K-01` Diagnóstico rápido del repo y del entorno
- [ ] `K-02` Respaldo integral ejecutado
- [ ] `K-03` Respaldo verificado y restaurable
- [ ] `K-04` Punto de restauración Git identificado
- [ ] `K-05` Clon paralelo preparado
- [ ] `K-06` Restauración de prueba documentada
- [ ] `K-07` Documentación actualizada
- [ ] `K-08` Push controlado a GitHub

### Esta Iteración

- [ ] Mueve aquí solo lo que vas a hacer hoy

### En Curso

- [ ] Deja aquí una sola tarjeta operativa a la vez

### Bloqueado

- [ ] Anota el bloqueo real y el comando que falló

### Hecho

- [ ] Mueve aquí solo lo validado con evidencia

## 4. Tarjetas y Criterio de Salida

### `K-01` Diagnóstico rápido del repo y del entorno

Objetivo:

- confirmar estado Git
- confirmar stack activo
- confirmar dónde responde PostgreSQL
- confirmar si `media/` vive en host o en Docker

Comandos base:

```bash
cd /Users/admin/Documents/project_secu_juridi
git status -sb
docker compose ps
readlink backups/latest
```

Criterio de salida:

- sabes si el repo tiene cambios locales
- sabes si el camino real es `docker` o `direct`
- sabes qué carpeta o volumen contiene `media`

Evidencia que debes anotar:

- rama actual
- cambios pendientes
- stack activo

### `K-02` Respaldo integral ejecutado

Objetivo:

- generar respaldo formal de base, `media`, código y `.env`

Comando base:

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/backup_full.sh
```

Criterio de salida:

- existe una carpeta nueva en `backups/YYYY-MM-DD/...`
- existe `manifest.env`
- existe `checksums.sha256`
- existe dump de BD
- existe respaldo de código
- existe respaldo de `.env`

Evidencia que debes anotar:

- ruta exacta del respaldo generado

### `K-03` Respaldo verificado y restaurable

Objetivo:

- probar que el respaldo no solo existe, sino que sirve

Comando base:

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/verify_backup.sh backups/latest
```

Criterio de salida:

- `Resultado general: OK`
- restauración temporal de la base exitosa
- conteo de tablas y `django_migrations` coincide
- `media` extraíble

Evidencia que debes anotar:

- ruta del reporte `backup_verification_*.md`

### `K-04` Punto de restauración Git identificado

Objetivo:

- dejar una referencia Git clara antes de evolucionar

Comandos base:

```bash
cd /Users/admin/Documents/project_secu_juridi
git log --oneline --decorate -3
git tag --list 'blindaje-*'
```

Si corresponde crear uno nuevo:

```bash
git tag -a blindaje-operativo-$(date +%Y%m%d-%H%M%S) -m "Punto de restauracion antes de evolucion"
```

Criterio de salida:

- tienes commit identificable
- tienes tag local o remoto si aplica

Evidencia que debes anotar:

- hash del commit
- nombre del tag

### `K-05` Clon paralelo preparado

Objetivo:

- trabajar en copia aislada sin romper la instalación estable

Comando base:

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/prepare_parallel_clone.sh --target-dir ../project_secu_juridi_dev
```

Criterio de salida:

- existe `../project_secu_juridi_dev`
- el clon levanta stack propio
- el clon responde en puertos alternos
- `python manage.py check` pasa dentro del clon

Evidencia que debes anotar:

- ruta del clon
- URL del clon
- puerto PostgreSQL del clon

### `K-06` Restauración de prueba documentada

Objetivo:

- tener el paso a paso para volver a levantar el sistema sin adivinar

Ruta guía:

- [RESPALDOS_Y_RESTAURACION.md](/Users/admin/Documents/project_secu_juridi/docs/RESPALDOS_Y_RESTAURACION.md)
- [RESTAURACION_TOTAL_PASO_A_PASO.md](/Users/admin/Documents/project_secu_juridi/docs/RESTAURACION_TOTAL_PASO_A_PASO.md)

Criterio de salida:

- sabes qué comandos ejecutar
- sabes en qué orden levantar `db/redis` y luego `web/worker/nginx`
- sabes cómo restaurar `media`

Evidencia que debes anotar:

- ruta del documento actualizado

### `K-07` Documentación actualizada

Objetivo:

- no dejar el blindaje solo “en la cabeza”

Archivos mínimos a revisar:

- [diagnostico_blindaje_inicial.md](/Users/admin/Documents/project_secu_juridi/docs/diagnostico_blindaje_inicial.md)
- [RESPALDOS_Y_RESTAURACION.md](/Users/admin/Documents/project_secu_juridi/docs/RESPALDOS_Y_RESTAURACION.md)
- [FLUJO_CLON_PARA_EVOLUCION.md](/Users/admin/Documents/project_secu_juridi/docs/FLUJO_CLON_PARA_EVOLUCION.md)

Criterio de salida:

- los comandos siguen coincidiendo con la realidad del repo
- la evidencia apunta al respaldo vigente

### `K-08` Push controlado a GitHub

Objetivo:

- subir solo lo que realmente quieres publicar

Comandos base:

```bash
cd /Users/admin/Documents/project_secu_juridi
git status -sb
git log --oneline --decorate -5
```

Criterio de salida:

- sabes si la rama está `ahead`
- sabes si empujarás commits previos no relacionados
- sabes si hay cambios locales sin commit que no deben mezclarse

Evidencia que debes anotar:

- rama
- hashes a publicar
- comando exacto de `git push`

## 5. Rutina Mínima Recurrente

Si tienes poco tiempo, esta es la secuencia mínima segura:

1. `git status -sb`
2. `./scripts/backups/backup_full.sh --verify`
3. `git tag -a blindaje-operativo-...`
4. `./scripts/backups/prepare_parallel_clone.sh --target-dir ../project_secu_juridi_dev`
5. trabajar en el clon

## 6. Criterio de “No Avanzar”

Detente si ocurre cualquiera de estos casos:

- el respaldo no genera `manifest.env`
- `verify_backup.sh` no termina en `OK`
- el clon levanta contenedores pero `web` no queda saludable
- el push va a mezclar commits que no querías subir
- vas a tocar el original sin haber validado el clon

## 7. Cierre de Iteración

Antes de dar por cerrada una iteración de blindaje, confirma:

- [ ] hay respaldo vigente
- [ ] hay reporte de verificación
- [ ] hay tag o commit identificable
- [ ] hay clon operativo o restauración probada
- [ ] la documentación quedó actualizada
- [ ] sabes exactamente qué vas a empujar a GitHub
