"""Custom template filters for tramites."""
from __future__ import annotations

from django import template

from tramites.services import feature_flags

register = template.Library()


@register.filter(name="abs_value")
def abs_value(value):
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value


@register.simple_tag(takes_context=True)
def feature_enabled(context, code: str, default_if_missing: bool = True):
    request = context.get("request")
    user = getattr(request, "user", None) if request is not None else None
    return feature_flags.is_enabled(code, user, default_if_missing=default_if_missing)
