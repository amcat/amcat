"""Menu is defined here. Any error in one of the urls-modules may lead to
unexpected errors here. Please handle with care!"""
from django.core.urlresolvers import reverse, resolve
from django.core.cache import cache
from django.conf import settings

from django.template.loader import get_template
from django.template import Context

from django.core.urlresolvers import Resolver404

import inspect

NMC = settings.NAVIGATOR_MENU_CACHE
NM = settings.NAVIGATOR_MENU

import logging; log = logging.getLogger(__name__)

def rev(view):
    """This converts a view string into an url. If an url is
    already given, this function returns it.
        
    @param view: view to convert
    @type view: str or unicode"""
    if '/' in view or view.startswith('http:'): return view
    return reverse(view)

def sort(item):
    """Function passed to sort() to sort NM"""
    return len(rev(item[1])) if item[1] else -1

def _get_module(view):
    if not callable(view):
        try:
            view = resolve(view).func
        except Resolver404:
            view = resolve(reverse(view)).func
        
    return inspect.getmodule(view)

def getSelected(menu, url):
    """Return label of selected item"""
    try:
        this_view = resolve(url).func
    except Resolver404:
        return
    this_view = ".".join((_get_module(this_view).__name__, this_view.__name__))

    views = dict((view, lbl) for lbl, view in menu if view)

    if this_view in views: 
        return views[this_view]

    mods = [(_get_module(view).__name__, lbl) for lbl, view\
            in menu if (view and not view.startswith('http:'))]
    mods.sort(key=lambda x: -len(x[0]))

    for mod, label in mods:
        if this_view.startswith(mod):
            return label

def _render(request):
    selected = getSelected([(i[0], i[1]) for i in NM], request.path)

    for item in NM:
        label, view = item[0], item[1]
        role = item[2] if len(item) == 3 else 0

        try:
            profile = request.user.get_profile()
        except AttributeError:
            pass # no profile, no developer role
        else:
            if profile.role.id >= role:
                yield(label, rev(view) if view else None, (label==selected))

def render(request):
    rendergen = _render(request)
    
    t = get_template("navigator/menu.html")
    c = Context({'menu' : list(rendergen)})
    menu = t.render(c)
    
    cache.set(NMC % request.path, menu)
    
    return menu
