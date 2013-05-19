from .. import menu

from amcat.tools import toolkit

from django.core.urlresolvers import reverse

from django.core.cache import cache
from django.conf import settings
from django import template
register = template.Library()

@register.filter
def render_menu(request):
    # Get menu from cache or render menu
    #return menu.render(request)
    return (cache.get(settings.NAVIGATOR_MENU_CACHE % request.path) or menu.render(request))
render_menu.is_safe = True

@register.filter
def tab_url(view, arg=None):
    """
    Filter specifically written (but no limited to) reversing tab-
    urls. This function overcomes the limitations of the normal url
    tag, as it can process variables.

    @type view: string, unicode
    @param view: view which needs to be reverted to an url.

    @type arg: whatever your view requires
    @param arg: args passed to reverse()
    """
    if arg is None:
        return reverse(view)
    elif isinstance(arg, dict):
        append = arg.pop("APPEND")
        url = reverse(view, kwargs=arg)
        if append: url += append
        return url
    else:
        return reverse(view, args=toolkit.totuple(arg))
tab_url.is_safe = True
