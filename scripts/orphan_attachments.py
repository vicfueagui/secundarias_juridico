#!/usr/bin/env python3
"""List and optionally clean orphan file references in tramites models.

An orphan record is one that stores a file path in DB but the file does not
exist in the configured Django storage backend.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _bootstrap_django() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:  # pragma: no cover - optional import
        load_dotenv = None

    if load_dotenv is not None:
        load_dotenv(ROOT_DIR / ".env", override=False)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "asesores_especializados.settings")

    import django

    django.setup()


@dataclass(frozen=True)
class Target:
    key: str
    label: str
    model_path: str
    field_name: str
    action: str  # "clear" or "delete"


TARGETS: tuple[Target, ...] = (
    Target(
        key="caso_minuta",
        label="CasoInterno.minuta",
        model_path="tramites.models.CasoInterno",
        field_name="minuta",
        action="clear",
    ),
    Target(
        key="tramite_minuta",
        label="TramiteCaso.minuta",
        model_path="tramites.models.TramiteCaso",
        field_name="minuta",
        action="clear",
    ),
    Target(
        key="minuta_caso_archivo",
        label="MinutaCaso.archivo",
        model_path="tramites.models.MinutaCaso",
        field_name="archivo",
        action="delete",
    ),
    Target(
        key="minuta_tramite_archivo",
        label="MinutaTramite.archivo",
        model_path="tramites.models.MinutaTramite",
        field_name="archivo",
        action="delete",
    ),
)


def _import_model(path: str):
    module_name, class_name = path.rsplit(".", 1)
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


def _iter_targets(selected_keys: Iterable[str]) -> list[Target]:
    selected = {key.strip() for key in selected_keys if key.strip()}
    if not selected:
        return list(TARGETS)
    index = {t.key: t for t in TARGETS}
    invalid = sorted(selected.difference(index))
    if invalid:
        raise SystemExit(f"Targets invalidos: {', '.join(invalid)}")
    return [index[key] for key in sorted(selected)]


def _scan_orphans(target: Target) -> dict:
    from django.core.files.storage import default_storage

    model = _import_model(target.model_path)
    query = (
        model.objects.exclude(**{f"{target.field_name}__isnull": True})
        .exclude(**{target.field_name: ""})
        .only("pk", target.field_name)
    )

    total_with_reference = 0
    orphans: list[dict[str, str | int]] = []
    scan_errors: list[dict[str, str | int]] = []

    for obj in query.iterator(chunk_size=500):
        total_with_reference += 1
        file_ref = getattr(obj, target.field_name)
        path = getattr(file_ref, "name", "") or ""
        path = str(path).strip()
        if not path:
            continue
        try:
            exists = default_storage.exists(path)
        except Exception as exc:  # pragma: no cover - defensive path
            scan_errors.append({"id": obj.pk, "path": path, "error": str(exc)})
            continue
        if not exists:
            orphans.append({"id": obj.pk, "path": path})

    return {
        "target_key": target.key,
        "label": target.label,
        "action": target.action,
        "model_path": target.model_path,
        "field_name": target.field_name,
        "total_with_reference": total_with_reference,
        "orphans_count": len(orphans),
        "scan_errors_count": len(scan_errors),
        "orphans": orphans,
        "scan_errors": scan_errors,
    }


def _apply_cleanup(scan_result: dict) -> dict:
    target = next(t for t in TARGETS if t.key == scan_result["target_key"])
    model = _import_model(target.model_path)
    orphan_ids = [row["id"] for row in scan_result["orphans"]]

    if not orphan_ids:
        return {"applied": 0, "mode": target.action}

    if target.action == "clear":
        updated = model.objects.filter(pk__in=orphan_ids).update(**{target.field_name: None})
        return {"applied": updated, "mode": "clear"}

    deleted, _ = model.objects.filter(pk__in=orphan_ids).delete()
    return {"applied": deleted, "mode": "delete"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lista y limpia referencias huerfanas de archivos adjuntos en tramites."
    )
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help=(
            "Target a procesar (puedes repetir): "
            "caso_minuta, tramite_minuta, minuta_caso_archivo, minuta_tramite_archivo. "
            "Por defecto procesa todos."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica limpieza real. Sin esto, solo lista (dry-run).",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=20,
        help="Cuantos orfanos mostrar por target en consola (default: 20).",
    )
    parser.add_argument(
        "--report",
        default="",
        help="Ruta opcional para guardar reporte JSON completo.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    _bootstrap_django()

    from django.db import transaction

    targets = _iter_targets(args.target)
    started_at = datetime.now(timezone.utc).isoformat()

    scan_results = []
    total_orphans = 0
    total_errors = 0

    print("=== Auditoria de adjuntos huerfanos ===")
    print(f"Modo: {'APPLY' if args.apply else 'DRY-RUN'}")
    print("")

    for target in targets:
        result = _scan_orphans(target)
        scan_results.append(result)
        total_orphans += result["orphans_count"]
        total_errors += result["scan_errors_count"]

        print(
            f"- {result['label']}: refs={result['total_with_reference']} "
            f"huerfanos={result['orphans_count']} errores_scan={result['scan_errors_count']}"
        )
        for row in result["orphans"][: max(0, args.show)]:
            print(f"    id={row['id']} path={row['path']}")
        if result["orphans_count"] > args.show:
            pending = result["orphans_count"] - args.show
            print(f"    ... y {pending} mas")

    applied_summary = {}
    if args.apply:
        print("")
        print("=== Aplicando limpieza ===")
        with transaction.atomic():
            for result in scan_results:
                applied = _apply_cleanup(result)
                applied_summary[result["target_key"]] = applied
                print(f"- {result['label']}: {applied['mode']} => {applied['applied']} registros")

    ended_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "started_at": started_at,
        "ended_at": ended_at,
        "apply_mode": args.apply,
        "targets": [t.key for t in targets],
        "total_orphans": total_orphans,
        "total_scan_errors": total_errors,
        "scan_results": scan_results,
        "applied_summary": applied_summary,
    }

    if args.report:
        report_path = Path(args.report)
        if not report_path.is_absolute():
            report_path = ROOT_DIR / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print("")
        print(f"Reporte JSON: {report_path}")

    print("")
    print(
        f"Resumen final: huerfanos={total_orphans} "
        f"errores_scan={total_errors} modo={'APPLY' if args.apply else 'DRY-RUN'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
