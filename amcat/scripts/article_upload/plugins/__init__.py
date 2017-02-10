
def _load_plugins():
    import sys
    import pkgutil
    import importlib.util
    import logging
    import os
    from collections import OrderedDict
    from amcat.scripts.article_upload.upload import UploadScript

    def import_module(loader, module_name, package=__package__):
        """
        Load the module if it doesn't exist yet, otherwise get the existing module.
        @param loader: the loader for the module
        @param module_name: the name of the module
        @return: The loaded module.
        """
        spec = loader.find_spec(modname, package)
        fullname = importlib.util.resolve_name("." + spec.name, package)
        log.debug(fullname)
        if fullname in sys.modules:
            return sys.modules[fullname]
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[fullname] = mod
        return mod

    def get_uploadscript(module):
        """
        Returns the first found module member that is a subclass of UploadScript.
        @param module: Any python module
        @return: The subclass, if it exists. Otherwise None.
        """
        for k, v in module.__dict__.items():
            if type(v) is type and issubclass(v, UploadScript):
                return v

    # Expand the package path to include other plugin directories.
    __path__ = pkgutil.extend_path([
        os.path.expanduser("~/amcat_upload_plugins")
    ], __name__)

    log = logging.getLogger(__name__)
    log.info("Loading upload plugins")
    plugins = []
    for loader, modname, ispkg in pkgutil.iter_modules(__path__):
        log.debug("loading {}".format(modname))
        try:
            mod = import_module(loader, "." + modname)
            upl_cls = get_uploadscript(mod)
            if upl_cls is None:
                raise Exception("UploadScript subclass not found.")

            plugins.append((upl_cls.__name__, upl_cls))
        except Exception as e:
            log.error("Could not load plugin module {}: {}".format(modname, e))

    log.info("Loaded {} upload plugins.".format(len(plugins)))
    return OrderedDict(sorted(plugins))

plugins = _load_plugins()
