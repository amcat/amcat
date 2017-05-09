def _init():
    global __path__
    import os
    import pkgutil
    import importlib
    import logging

    log = logging.getLogger(__name__)

    USER_DIRS = [
        os.path.expanduser("~/amcat_plugins/upload")
    ]
    __path__ += USER_DIRS

    def report_error(name):
        log.error("Error while loading plugin module or package: {}".format(name))

    found_plugins = []

    for _, module, ispkg in pkgutil.walk_packages(__path__, prefix="{}.".format(__name__), onerror=report_error):
        if ispkg:
            continue
        try:
            importlib.import_module(module)
            found_plugins.append(module)
        except Exception as e:
            log.error("An error occured while importing plugin '{module}': {e}.".format(**locals()))

    log.debug("Imported plugin modules {}".format(found_plugins))

_init()
