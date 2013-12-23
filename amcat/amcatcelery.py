from __future__ import absolute_import

from celery import Celery
from django.conf import settings

app = Celery('amcat')
app.config_from_object('settings.scraping_celery')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

