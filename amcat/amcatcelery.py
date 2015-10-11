from __future__ import absolute_import

import socket
import amcat
import os

from celery import Celery
from django.conf import settings

app = Celery('amcat')
app.config_from_object('settings.celery')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def status(self):
    
    loc = os.path.normpath(os.path.join(os.path.dirname(amcat.__file__),
                                        ".."))
    
    result = {"amcat_version": amcat.__version__,
              "hostname": socket.gethostname(),
              "folder": loc,
              "default_celery_queue": app.conf.CELERY_DEFAULT_QUEUE}
    if self.request.id:
        result.update({"worker": self.request.hostname,
                       "routing_key": self.request.delivery_info['routing_key'],
                       "exchange": self.request.delivery_info['exchange'],
                       "task_id": self.request.id})
    return result

