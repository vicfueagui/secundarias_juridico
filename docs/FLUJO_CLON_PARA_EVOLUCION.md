# Flujo de Clon Paralelo Para Evolución

## 1. Objetivo

Tener dos espacios separados:

- **original estable** para referencia y respaldo
- **copia de evolución** para cambios futuros

Esto evita romper la referencia institucional mientras se sigue desarrollando.

## 2. Recomendación para el estado real del repo hoy

Hoy el árbol Git está sucio. Por eso, la opción más segura y simple **ahorita** es copia hermana del working tree.

Comando recomendado:

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/prepare_parallel_clone.sh --target-dir ../project_secu_juridi_dev
```

Qué hace:

- copia el working tree actual a una carpeta hermana
- conserva el estado funcional actual que todavía no está congelado en commit
- excluye `.venv`, `backups`, `staticfiles`, `node_modules`, dumps, tarballs y logs pesados
- ajusta `.env` del clon para no chocar con puertos del original
- publica PostgreSQL del clon en un puerto propio para trabajo local con `.venv`
- restaura base y `media` desde el respaldo más reciente
- deja trazabilidad con `.clone_source_commit` y `.clone_source_status`
- no copia `.git`; esta opción sirve para trabajar aislado, no para hacer commits desde esa carpeta

## 3. Cuándo usar `git worktree`

Usa `worktree` cuando ya fijaste un punto limpio con commit/tag.

Comando recomendado en ese escenario:

```bash
cd /Users/admin/Documents/project_secu_juridi
git add .
git commit -m "chore: punto estable antes de evolucion"
git tag pre-evolucion-$(date +%Y%m%d-%H%M)
./scripts/backups/clone_worktree.sh --mode worktree --target-dir ../project_secu_juridi_dev --branch worktree/evolucion-$(date +%Y%m%d-%H%M) --ref HEAD
```

Ventaja:

- menor consumo de disco
- relación Git más limpia
- mejor trazabilidad de ramas

Advertencia:

- `git worktree` no arrastra cambios no confirmados

## 4. Orden recomendado de trabajo

1. Genera respaldo integral y verifícalo.
2. Si puedes, congela commit/tag del estado estable.
3. Crea la copia paralela.
4. Deja la carpeta original solo para referencia estable y respaldos.
5. Trabaja las mejoras en la copia paralela.

## 5. Comandos exactos

### Opción segura hoy: copia hermana

```bash
cd /Users/admin/Documents/project_secu_juridi
./scripts/backups/backup_full.sh --verify
./scripts/backups/prepare_parallel_clone.sh --target-dir ../project_secu_juridi_dev
```

### Opción posterior: worktree ya congelado

```bash
cd /Users/admin/Documents/project_secu_juridi
git add .
git commit -m "chore: punto estable antes de evolucion"
git tag pre-evolucion-$(date +%Y%m%d-%H%M)
./scripts/backups/clone_worktree.sh --mode worktree --target-dir ../project_secu_juridi_dev --branch worktree/evolucion-$(date +%Y%m%d-%H%M) --ref HEAD
```

## 6. Validación realizada

El flujo de clon paralelo fue probado en este repositorio durante el blindaje.

Se confirmó que:

- crea la carpeta hermana correctamente
- registra `.clone_source_commit`
- registra `.clone_source_status`
- ya no arrastra `*.dump`, `*.tar.gz` ni `*.log` del raíz
- puede quedar listo con puertos y base separados del proyecto original
- fue validado operativo en `http://127.0.0.1:8081` con PostgreSQL expuesto en `127.0.0.1:5542`
- pasó `docker compose exec -T web python manage.py check`

## 7. Regla de oro

Primero protege.

Luego congela.

Luego evoluciona.

No mezcles la carpeta estable con la carpeta de cambio si el sistema ya está siendo usado.
