"""Template tags personalizados para formularios."""
from django import template

from licencias.utils import normalise_sistema

register = template.Library()


@register.filter(name='attr')
def get_attribute(obj, attr_name):
    """Obtiene un atributo de un objeto por nombre."""
    return getattr(obj, attr_name, None)


@register.filter(name="field")
def get_form_field(form, field_name):
    """Devuelve un campo del formulario usando el nombre proporcionado."""
    if not hasattr(form, "__getitem__"):
        return None
    try:
        return form[field_name]
    except KeyError:
        return None


@register.filter(name="add_class")
def add_class(field, css_class):
    """Agrega clases CSS al renderizado de un campo."""
    if hasattr(field, "as_widget"):
        attrs = field.field.widget.attrs.copy()
        existing = attrs.get("class", "")
        attrs["class"] = " ".join(filter(None, [existing, css_class]))
        return field.as_widget(attrs=attrs)
    return field


@register.filter(name="sistema_display")
def sistema_display(value):
    """Normaliza los valores del sistema (sostenimiento)."""
    return normalise_sistema(value)
