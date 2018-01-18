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

# set settings module and setup django - useful so you can import this first
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

import argparse
import logging

from django import forms
from django.core.files import File

from amcat.scripts.script import Script
from amcat.tools import  classtools

log = logging.getLogger(__name__)

###############################################################
##         Aux method for CLI invocation                     ##
###############################################################

def run_cli(cls=None):
    """Handle command line interface invocation of this script"""

    if cls is None:
        module = classtools.get_calling_module()
        cls = classtools.get_class_from_module(module, Script)

    parser = argument_parser_from_script(cls)
    args = parser.parse_args()
    options = args.__dict__

    verbose = options.pop("verbose", None)
    logging.basicConfig(format='[%(asctime)s] [%(name)s] %(message)s',
                        level=(logging.DEBUG if verbose else logging.INFO))
    logging.getLogger('requests').setLevel(logging.WARN)

    instance = cls(options)

    return instance.run()


def argument_parser_from_script(script_class):
    """Create an argparse.ArgumentParser from a Script class object"""
    parser = argparse.ArgumentParser(description=script_class.__doc__)
    for name, field in script_class.options_form().fields.items():
        add_argument_from_field(parser, name, field)
    
    parser.add_argument(*_get_option_argname(parser, 'verbose'),
                        help='Print debug output', action='store_true')
    
    return parser

def _get_option_argname(parser, optname):
    """Generate the --long and -short option name"""
    result = ["--"+optname]
    prefix = "-" + optname[0]
    if prefix not in parser._option_string_actions:
        result.append(prefix)
    return result
    
def add_argument_from_field(parser, name, field):
    """
    Call parser.add_argument with the appropriate parameters
    to add this django.forms.Field to the argparse.ArgumentParsers parser.
    """
    # set options name to lowercase variant, remember name for storage
    optname = name.lower()
    argname = ([optname] if (field.required and field.initial is None)
               else _get_option_argname(parser, optname))

    # determine help text from label, help_text, and default
    helpfields = [x for x in [field.label, field.help_text] if x]
    if field.initial is not None: helpfields.append("Default: {field.initial}".format(**locals()))
    if isinstance(field, forms.ChoiceField):
        if len(field.choices) > 10:
            helpfields.append("(>10 possible values)")
        else:
            helpfields.append("Possible values are %s" % "; ".join("%s (%s)" % (kv) for kv in field.choices))
    elif type(field) in _FIELD_HELP_MAP:
        helpfields.insert(0, _FIELD_HELP_MAP[type(field)])
    help = ". ".join(helpfields)

    # set type OR action_const as extra arguments depending on type
    args = {} # flexible parameters to add_argument
    if isinstance(field, forms.ModelMultipleChoiceField) or isinstance(field, forms.MultipleChoiceField):
        args["nargs"] = '+'
        argname = ['--' + optname] # problem: now the field appears to be optional, but at least it knows which values belong to this argument
    if isinstance(field, forms.BooleanField) and field.initial is not None:
        args["action"] = "store_const"
        args["const"] = not field.initial
    else:
        args["type"] = argument_type_from_field(field)

    if [name] != argname:
        args["dest"] =  name

    parser.add_argument(*argname, help = help, default=field.initial, metavar=name, **args)

_FIELD_MAP = {
    forms.IntegerField : int,
    forms.BooleanField : bool,
    forms.FileField : (lambda fn: File(open(fn))),
    }
_FIELD_HELP_MAP = {
    forms.IntegerField : "(number)",
    forms.FileField : "(filename)",
    }

def argument_type_from_field(field):
    """Get the proper python type to parse a command line option"""
    for (ftype, type) in _FIELD_MAP.items():
        if isinstance(field, ftype): return type
    return str
