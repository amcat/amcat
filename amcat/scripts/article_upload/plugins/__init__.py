def _init():
    global __path__, __all__, errors
    import os
    import pkgutil
    import importlib
    import logging
    USER_DIRS = [
        os.path.expanduser("~/amcat_upload_plugins"),
        os.path.expanduser("~/amcat_plugins/upload")
    ]
    __path__ += USER_DIRS

    __all__ = []

    log = logging.getLogger(__name__)
    for _, module, _ in pkgutil.iter_modules(__path__):
        log.debug("Importing plugin module {}".format(module))
        try:
            importlib.import_module("." + module, __package__)
            __all__.append(module)
        except Exception as e:
            log.error("An error occured while importing plugin '{module}': {e}.".format(**locals()))


_init()
