
import os
import resource
import socket

import amcat
from celery import Celery
from celery.loaders.base import BaseLoader
from django.conf import settings


class FileLimitingLoader(BaseLoader):
    """Reduces the open file limit on celery child processes."""
    def on_worker_process_init(self):
        import settings
        try:
            sl, hl = resource.getrlimit(resource.RLIMIT_NOFILE)
            new_sl = settings.amcat_config.getint("celery", "worker_process_file_limit", fallback=16000)
            resource.setrlimit(resource.RLIMIT_NOFILE, (new_sl, hl))
        except (resource.error, ValueError):
            pass  # just keep the current limit
        return super().on_worker_process_init()


app = Celery('amcat', loader='amcat.amcatcelery:FileLimitingLoader')
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

