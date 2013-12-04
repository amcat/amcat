from __future__ import absolute_import

from settings import celery as settings_celery
import celery
from celery import Celery
from django.conf import settings

app = Celery('amcat')
app.config_from_object(settings_celery)
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

