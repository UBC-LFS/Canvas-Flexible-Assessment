from django import template

register = template.Library()


@register.filter(name='split')
def split(value, delimiter):
    """Split a string by a delimiter and return a list."""
    if value is None:
        return []
    return value.split(delimiter)

@register.filter(name='to_float')
def to_float(value):
    """Convert a value to float, return 0 if conversion fails"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0
