from xml.sax.saxutils import escape, quoteattr

from django.utils.safestring import mark_safe
from django.template import Library

register = Library()
register.filter('xmlescape', lambda o: mark_safe(escape(o)))
register.filter('quoteattr', lambda o: mark_safe(quoteattr(o)))
