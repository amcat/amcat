"""AmCAT python libraries"""


# from http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
from amcat.amcatcelery import app
from amcat._version import __version__
from django.apps import AppConfig

default_app_config = 'amcat.AmCATAppConfig'


class AmCATAppConfig(AppConfig):
    name = 'amcat'
    verbose_name = "AmCAT"

    def ready(self):
        from amcat.tools.amcates import delete_test_indices
        from django.conf import settings

        if settings.TESTING:
            print("Destroying old elasticsearch test indices..")
            delete_test_indices()
