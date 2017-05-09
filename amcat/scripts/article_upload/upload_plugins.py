import logging
from collections import OrderedDict
from typing import Mapping, Type

from amcat.models import Project
from amcat.scripts.article_upload.upload import UploadScript

log = logging.getLogger(__name__)

_registered_plugins = {}


class PluginError(Exception):
    pass


class UploadPlugin:
    """
    A callable class decorator that registers the plugin to AmCAT. This decorator is required for the plugin
    in order for it to be registered as an uploader.

    Example Usage:
        >>> @UploadPlugin(label="My Plugin")
        >>> class MyPlugin:
        >>>     ...
    """

    def __init__(self, *,
                 label: str = None,
                 name: str = None,
                 default: bool = False):
        """
        @param author:  The author of this plugin. Not required, but it could be useful.
        @param label:   A human readable name. If not given, the `name` will be used.
        @param name:    A name to be used as unique identifier. Must be unique.
                         If not given, the __name__ attribute of the class will be used.
        @param default: Whether to use this as a default uploader in a new project.
        """
        self.default = default
        self.script_cls = None

        self._label = label
        self._name = name

    def __call__(self, script_cls: Type[UploadScript]) -> Type[UploadScript]:
        """
        Registers the class as a plugin. The class has to be a subclass of UploadScript.
        Sets self as the class' 'plugin_info' attribute.

        @param script_cls: The script class.
        @return: The script class itself.
        """
        if self.script_cls is not None:
            raise self._get_error("already_registered")
        if not issubclass(script_cls, UploadScript):
            raise self._get_error("not_an_uploadscript", script_cls=script_cls)

        self.script_cls = script_cls

        if not hasattr(script_cls, 'plugin_info'):
            setattr(script_cls, 'plugin_info', self)

        # name self after script class if name doesn't exist yet
        if self.name is None:
            if self.script_cls.__name__ in _registered_plugins:
                # use module prefix in case of conflict
                self._name = "{0.__module__}.{0.__name__}".format(self.script_cls)
            else:
                self._name = self.script_cls.__name__

        if self.name in _registered_plugins:
            raise self._get_error("duplicate_name")
        _registered_plugins[self.name] = self
        return script_cls

    @property
    def __name__(self) -> str:
        return self.name

    @property
    def label(self) -> str:
        """
        A human readable label.
        """
        if self._label is None:
            self._label = self.name
        return self._label

    @property
    def name(self) -> str:
        """
        A unique name that serves as the identifier of the plugin.
        """
        return self._name


    _errors = {

        "already_registered": (PluginError, "A class was already registered to this plugin: "
                                            "'{self.script_cls.__module__}.{self.script_cls.__name__}'."),

        "not_an_uploadscript": (PluginError, "Class '{script_cls.__module__}.{script_cls.__name__}' "
                                             "is not a subclass of UploadScript"),

        "duplicate_name": (PluginError, "A plugin with name '{self.name}' was already registered: "
                                        "'{self.script_cls.__module__}.{self.script_cls.__name__}'")
    }

    def _get_error(self, message_key, **kwargs):
        format_kwargs = {
            "self": self,
            "cls": self.__class__,
            **kwargs
        }
        err_cls, msg = self._errors[message_key]
        msg = msg.format(**format_kwargs)
        return err_cls(msg)


def get_project_plugins(project: Project) -> Mapping[str, UploadPlugin]:
    """
    Retrieves all plugins that are enabled in the project.

    @param project: A Project object
    @return:
    """
    all_plugins = get_upload_plugins()
    enabled_plugins = {k: v.default for k, v in all_plugins.items()}
    enabled_plugins.update((p.name, p.enabled) for p in project.upload_plugins.all())
    return OrderedDict((k, v) for k, v in all_plugins.items() if enabled_plugins[k])


def get_upload_plugins() -> Mapping[str, UploadPlugin]:
    """
    Returns all known plugins.
    """
    global _registered_plugins

    if not _registered_plugins:
        # noinspection PyUnresolvedReferences
        import amcat.scripts.article_upload.plugins
        _registered_plugins = OrderedDict(sorted(_registered_plugins.items(), key=lambda x: x[1].label.lower()))
        log.debug("Registered {} plugins".format(len(_registered_plugins)))
        log.debug(list(_registered_plugins.keys()))

    return _registered_plugins


def get_upload_plugin(name: str) -> UploadPlugin:
    """
    Gets an upload plugin by name, and returns the UploadPlugin object.
    """
    return get_upload_plugins()[name]
