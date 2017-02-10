

def _init():
    global __path__, __all__
    import os
    USER_DIRS = [
        os.path.expanduser("~/amcat_upload_plugins"),
        os.path.expanduser("~/amcat_plugins/upload")
    ]
    __path__ += USER_DIRS

    __all__ = []
_init()


def load_plugins():
    """
    Forces an import for every module in the plugins package
    """
    import pkgutil
    import importlib
    import logging
    log = logging.getLogger(__name__)
    for _, module, _ in pkgutil.iter_modules(__path__):
        log.debug("Importing plugin module {}".format(module))
        try:
            importlib.import_module("." + module, __package__)
        except Exception as e:
            log.error("Failed to import uploader {}: {}".format(module, e))
