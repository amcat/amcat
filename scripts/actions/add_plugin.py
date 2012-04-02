#!/usr/bin/python

##########################################################################
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
Script add a plugin to the db
"""

import os
import logging; log = logging.getLogger(__name__)

from django import forms
from django.forms.widgets import HiddenInput

from amcat.scripts.script import Script
from amcat.scripts.tools import cli
from amcat.models.plugin import Plugin
from amcat.models.analysis import Analysis
from amcat.models.language import Language
from amcat.tools import toolkit

class AddPluginForm(forms.ModelForm):

    analysis_language = forms.ModelChoiceField(queryset=Language.objects.all(), required=False,
         help_text='If given, also creates a preprocessing analysis with the given language')

    class Meta:
        model = Plugin
        fields = ('class_name', 'module', 'label', 'description', 'type', 'active')

    def __init__(self, *args, **kargs):
        super(AddPluginForm, self).__init__(*args, **kargs)
        for (field, default) in [('module', 'class name'), ('label', 'class name'),
                                 ('description', 'doc string'), ('type', 'superclass')]:
            self.fields[field].required = False
            self.fields[field].help_text = 'Default based on %s' % default

    @classmethod
    def get_empty(cls, type=None, **_options):
        f = cls()
        if type is not None:
            f.fields['type'].initial = type
            f.fields['type'].widget = HiddenInput()

            if type != 'amcat.nlp.analysisscript.AnalysisScript':
                f.fields['analysis_language'].widget = HiddenInput()

        return f

class AddPlugin(Script):
    """Add a user to the database. A new DB user will be created,
    and the user will be added to the users table.

    If the user already exists in the database but not in the users table,
    he/she will be added to that table.
    """

    options_form = AddPluginForm
    output_type = Plugin

    def _bind_form(self, *args, **kargs):
        form = super(AddPlugin, self)._bind_form(*args, **kargs)
        form.data = form.data.copy()
        
        if form.data['module'] is None:
            if "/" in form.data['class_name']:
                # filename, so find and import module and class is first defined Script class
                form.data['module'] = guess_module(form.data['class_name'])
                cls = toolkit.get_class_from_module(form.data['module'], Script)
                form.data['class_name'] = cls.__name__
            elif "." in form.data['class_name']:
                # qualified class name, so split into module and class
                mod, cls = form.data['class_name'].rsplit(".", 1)
                form.data['module'], form.data['class_name'] =  mod, cls
            else:
                raise forms.ValidationError("If module is not given,"
                                            "class name needs to be fully qualified")
        elif set(form.data['class_name']) & {".","/"}:
            raise forms.ValidationError("If module name is given, class name %r cannot contain"
                                        ". or / characters" % form.data['class_name'])
        plugin_class = toolkit.import_attribute(form.data['module'], form.data['class_name'])
        if not form.data['label']:
            form.data['label'] = form.data['class_name']
        if not form.data['description']:
            if plugin_class.__doc__ is None:
                plugin_module =  toolkit.import_attribute(form.data['module'])
                form.data['description'] = plugin_module.__doc__.strip()
            else:
                form.data['description'] = plugin_class.__doc__.strip()
        if form.data['type'] is None:
            superclass = plugin_class.__bases__[0]
            form.data['type'] = ".".join((superclass.__module__, superclass.__name__))

        lan = form.data['analysis_language']
        if lan:
            try:
                int(lan)
            except ValueError:
                if isinstance(lan, basestring):
                    lan = Language.objects.get(label=lan)
                form.data['analysis_language'] = lan.id

        return self.options_form(form.data) # hack: re-bind form to propagate data


    def run(self, _input=None):
        language = self.options.pop('analysis_language')
        p = Plugin.objects.create(**self.options)
        if language:
            a = Analysis.objects.create(language=language, plugin=p)
        return p


def get_classes(type, module="amcat.scripts"):
    for c in toolkit.get_classes_from_module(module, type):
        try:
            Plugin.objects.get(class_name=c.__name__, module=c.__module__)
        except Plugin.DoesNotExist:
            yield c
    p = toolkit.import_attribute(module)
    if "__init__.py" in p.__file__:
        # package -> loop contents
        dir = os.path.dirname(p.__file__)
        for item in os.listdir(dir):
            fn = os.path.join(dir, item)
            if os.path.isdir(fn):
                if os.path.exists(os.path.join(fn, "__init__.py")):
                    for c in get_classes(type, module + "." + item):
                        yield c
            if item.endswith(".py") and item != "__init__.py" and '#' not in item:
                mod = item[:-3]
                for c in get_classes(type, module + "." + item[:-3]):
                    yield c

if __name__ == '__main__':
    cli.run_cli()
