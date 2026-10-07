import re

from django import template

register = template.Library()

_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


@register.simple_tag
def safe_color(value, fallback):
    """Return *value* only when it is a safe CSS hex color, else *fallback*.

    Used to inject administrator-configured brand colors into inline CSS
    without allowing arbitrary CSS injection.
    """
    if value and _HEX_COLOR_RE.match(str(value).strip()):
        return str(value).strip()
    return fallback
