"""Utilidades compartidas para la aplicación de licencias."""

from __future__ import annotations


def normalise_sistema(value: str | None) -> str:
    """Normaliza el valor del sistema del CCT."""
    if value is None:
        return ""
    normalized = (value or "").strip()
    if normalized.upper() == "FEDERAL TRANSFERIDO":
        return "FEDERAL"
    return normalized

