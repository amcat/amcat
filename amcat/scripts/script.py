###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################


"""
Interface definition and general functionality for amcat Scripts.

A Script is a generic "pluggable" functional element that can be
called from e.g. the Django site, as a standalone web interface, or as
a command line script.
"""

from django import forms
from django.http import QueryDict
from django.utils.datastructures import MergeDict
from amcat.forms import validate
from amcat.models.plugin import Plugin, PluginType


class Script(object):
    """
    'Abstract' class representing a modular piece of
    functionality. Scripts have three key parameters, specified as class variables:
    - input_type: a class representing the type of input expected by the script, such as
      None, unicode, Table, or ArticleList. The command line equivalent would be
      a (deserialized) stdin stream
    - options: a Django form of required and optional options. The CLI equivalent
      are the command line options and arguments. Can be None
    - output_type: a class representing the output that the script will produce.
    """

    input_type = None
    options_form = None
    output_type = None

    def __init__(self, options=None, **kargs):
        """Default __init__ validates and stores the options form"""
        if self.options_form is None:
            self.options = self.options_raw = None
        else:
            self.bound_form = self._bind_form(options, **kargs)
            self._validate_form()
            self.options = self.bound_form.cleaned_data


    def run(self, input=None):
        """Run is invoked with the input, which should be of type input_type,
        and should return a result of type output_type or raise an exception"""
        return self._run(**self.options)

    def _run(self, **options):
        pass

    def _validate_form(self):
        """Validate self.bound_form, raising an exception if invalid"""
        validate(self.bound_form)


    def _bind_form(self, options=None,  **kargs):
        """
        Create a bound form from the options and key-word arguments. Will raise
        a ValueError if no bound instance of the form for this script could be
        created

        @param options: Either a bound options form or a dict with option value
                        with which to create a bound form
        @param kargs:   If options is None, keyword arguments to use to create a
                        bound form
        @return:        A bound form of type self.options_form
        """
        if isinstance(options, self.options_form):
            validate(options)
            if not options.is_valid:
                validate(self.bound_form)
            if not options.is_bound:
                raise ValueError("Please provide a bound options form")
            return options
        elif isinstance(options, forms.Form):
            raise ValueError("Invalid options form type: {0}".format(self.options_form))
        if not isinstance(options, (dict, QueryDict, MergeDict)):
            options = kargs
        # specify options as file as well, django will pick it from the right place
        # (why does django distinguish between POST and FILES as both are dicts...?)
        return self.options_form(options, options)

    @classmethod
    def get_empty_form(cls, **options):
        """
        Get an 'empty form', possibly initialized with options such as user or project
        """
        f = cls.options_form
        try:
            get_empty = f.get_empty
        except AttributeError:
            return f()
        else:
            return get_empty(**options)

    @classmethod
    def name(cls):
        return cls.__name__

    @classmethod
    def description(cls):
        return cls.__doc__

    @classmethod
    def module(cls):
        return cls.__module__

    @classmethod
    def get_plugin(cls):
        """
        Get the Plugin object corresponding to this class
        """
        qualified_name = ".".join([cls.__module__, cls.__name__])
        return Plugin.objects.get(class_name=qualified_name)

    @classmethod
    def get_plugin_type(cls):
        """
        Get the PluginType object corresponding to this class, if any
        If the corresponding plugin has a Type, return it.
        If not, check whether it 'is' a type, e.g. there is a type defined by this plugin
        """
        try:
            return cls.get_plugin().plugin_type
        except Plugin.DoesNotExist:
            # maybe we are the 'plugintype' instead of a plugin?
            qualified_name = ".".join([cls.__module__, cls.__name__])
            return PluginType.objects.get(class_name=qualified_name)
