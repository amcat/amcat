from collections import OrderedDict
from typing import Mapping, Iterable

import functools

from amcat.models import Project
from amcat.scripts.article_upload.upload import UploadScript

_registered_plugins = {}


class PluginError(Exception):
    pass


class UploadPlugin:
    """
    A callable class decorator that registeres the plugin to AmCAT. This decorator is required for the plugin
    in order for it to be registered as an uploader.

    Example Usage:
        >>> @UploadPlugin(label="My Plugin")
        >>> class MyPlugin:
        >>>     ...
    """

    def __init__(self, label: str = None, name: str = None, default: bool = False):
        """
        @param label:    A human readable name. If not given, the `name` will be used.
        @param name:    A name to be used as unique identifier. Must be unique.
                         If not given, the __name__ attribute of the class will be used.
        @param default: Whether to use this as a default uploader in a new project.
        """
        self._label = label
        self._name = name
        self.default = default
        self.script_cls = None

    def __call__(self, plugin_cls: type) -> type:
        if self.script_cls is not None:
            raise PluginError("A class was already registered.")
        if not issubclass(plugin_cls, UploadScript):
            raise PluginError("{} is not a subclass of UploadScript".format(plugin_cls))

        self.script_cls = plugin_cls
        if self.name in _registered_plugins:
            raise PluginError("A plugin with name '{}' was already registered.".format(self.name))
        _registered_plugins[self.name] = self
        return plugin_cls

    @property
    def __name__(self):
        return self.name
    @property
    def label(self):
        """
        A human readable label.
        """
        if self._label is None:
            self._label = self.name
        return self._label

    @property
    def name(self):
        """
        A unique name that serves as the identifier of the plugin.
        """
        if self._name is None:
            self._name = self.script_cls.__name__
        return self._name


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
    return _registered_plugins


def get_upload_plugin(name: str) -> UploadPlugin:
    """
    Gets an upload plugin by name, and returns the UploadPlugin object.
    """
    return get_upload_plugins()[name]

