from __future__ import annotations

from django.db.models import Prefetch

from tramites import models


def _resolve_group_override_values(reglas: list[bool]) -> bool | None:
    if not reglas:
        return None
    # Si existe conflicto entre grupos, prevalece OFF por seguridad.
    if any(value is False for value in reglas):
        return False
    return True


def is_enabled(codigo: str, user=None, *, default_if_missing: bool = True) -> bool:
    flag = models.FeatureFlag.objects.filter(codigo=codigo).first()
    if flag is None:
        return default_if_missing
    if not flag.habilitado:
        return False
    if not getattr(user, "is_authenticated", False):
        return flag.habilitado_por_defecto
    group_ids = list(user.groups.values_list("id", flat=True))
    reglas = list(
        models.FeatureFlagGrupo.objects.filter(flag=flag, grupo_id__in=group_ids).values_list(
            "habilitado", flat=True
        )
    )
    override = _resolve_group_override_values(reglas)
    if override is None:
        return flag.habilitado_por_defecto
    return bool(override)


def resolve_for_user(user) -> dict[str, bool]:
    flags = models.FeatureFlag.objects.all()
    if not getattr(user, "is_authenticated", False):
        return {flag.codigo: bool(flag.habilitado and flag.habilitado_por_defecto) for flag in flags}

    group_ids = list(user.groups.values_list("id", flat=True))
    flags = flags.prefetch_related(
        Prefetch(
            "asignaciones_grupo",
            queryset=models.FeatureFlagGrupo.objects.filter(grupo_id__in=group_ids),
        )
    )
    result: dict[str, bool] = {}
    for flag in flags:
        if not flag.habilitado:
            result[flag.codigo] = False
            continue
        reglas = [asignacion.habilitado for asignacion in flag.asignaciones_grupo.all()]
        override = _resolve_group_override_values(reglas)
        if override is None:
            result[flag.codigo] = bool(flag.habilitado_por_defecto)
        else:
            result[flag.codigo] = bool(override)
    return result
