from django.conf import settings
from django import template
register = template.Library()

@register.filter
def AMCAT_VERSION(a):
    """Return current AmCAT version based on mercurial repository"""
    # IS THIS ACTUALLY USED ANYWHERE?
    return settings.AMCAT_VERSION

AMCAT_VERSION.is_safe = True

# http://stackoverflow.com/questions/8000022
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def join_list(l, sep):
    "Join l by sep if it is a list"
    if not isinstance(l, (str, unicode)):
        try:
            return sep.join(l)
        except TypeError:
            pass
    return l
