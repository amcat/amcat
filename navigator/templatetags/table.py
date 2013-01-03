from django.conf import settings

from django import template
register = template.Library()

@register.filter
def table(view):
    # Get menu from cache or render menu
    pass

table.is_safe = True
