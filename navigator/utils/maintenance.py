"""
Maintenance mode middleware

Will put amcat into 'maintenance mode' if a file called "maintenance-mode" is present in
the amcat root folder (e.g. the folder returned by import amcat).

Inspired by https://pypi.python.org/pypi/django-maintenancemode (BSD License)
"""


import os.path
from django.core import urlresolvers
import logging
log = logging.getLogger(__name__)

class MaintenanceModeMiddleware(object):
    def process_request(self, request):
        import amcat
        fn = os.path.join(os.path.dirname(amcat.__file__), "maintenance-mode")

        if os.path.exists(fn):
            log.warn("AmCAT is in maintenance mode, returning 503!")

            resolver = urlresolvers.get_resolver(None)
            callback, param_dict = resolver._resolve_special('503')
            return callback(request, **param_dict)



