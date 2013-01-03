from django.conf import settings
from django import template
register = template.Library()

@register.filter
def AMCAT_VERSION(a):
    """Return current AmCAT version based on mercurial repository"""
    return settings.AMCAT_VERSION

AMCAT_VERSION.is_safe = True

