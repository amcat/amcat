from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe
from django.template import Library

import json

register = Library()

def jsonify(object):
    return mark_safe(json.dumps(object, cls=DjangoJSONEncoder))

register.filter('jsonify', jsonify)