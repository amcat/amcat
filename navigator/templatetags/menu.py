from amcat.tools import toolkit

from django.core.urlresolvers import reverse

from django.core.cache import cache
from django.conf import settings
from django import template
register = template.Library()

@register.simple_tag(takes_context=True)
def is_active(context, item_name, classnames="", var='context_category'):
    active_item = context.get(var)
    if item_name == active_item:
        classnames = (classnames + " active").strip()
    return ' class="{classnames}"'.format(**locals())
