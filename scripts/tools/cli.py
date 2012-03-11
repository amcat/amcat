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

from django import forms
from amcat.scripts.output import commandline
from amcat.scripts import scriptmanager
from amcat.scripts.script import Script
import argparse
import sys
from amcat.tools import toolkit, amcatlogging
import types

import logging; log = logging.getLogger(__name__)
#logging.basicConfig(format='[%(asctime)s] [%(name)s] %(message)s', level=logging.DEBUG)
#logging.getLogger('django.db.backends').setLevel(logging.ERROR)



###############################################################
##         Aux method for CLI invocation                     ##
###############################################################

def get_main_script(module):
    if type(module) == type(''):
	module_name = module
	module = __import__(module_name)
	for part in module_name.split('.')[1:]:
	    module = getattr(module, part)
    for name in dir(module):
	obj = getattr(module, name)
	if (isinstance(obj, (type, types.ClassType)) and
	    issubclass(obj, Script)):
	    return obj
    raise Exception("Cannot find Script module in %r" % module)

def run_cli(cls=None, handle_output=None):
    """Handle command line interface invocation of this script"""
    amcatlogging.setup()

    if cls is None:
	mod = toolkit.getCallingModule()
	cls = get_main_script(mod)

    if handle_output is None:
	handle_output = cls.output_type != None

    parser = argument_parser_from_script(cls)
    args = parser.parse_args()
    options = args.__dict__
    instance = cls(options)

    input = None
    if cls.input_type in (file, str, unicode):
	input = sys.stdin
    if cls.input_type in (str, unicode):
	input = input.read()
    if cls.input_type == unicode:
	input = input.decode('latin-1')

    out = instance.run(input)
    
    if handle_output:
        out = handleOutput(out, instance.output_type)
    return out

def handleOutput(out, output_type):
    cls = scriptmanager.findScript(output_type, str)
    if not cls:
        print(out)
    else:
        print cls().run(out)
            

def argument_parser_from_script(script_class):
    """Create an argparse.ArgumentParser from a Script class object"""
    parser = argparse.ArgumentParser(description=script_class.__doc__)
    used_prefixes = set("-h") # keep track of -X options used; -h -> help
    if script_class.options_form:
        form = script_class.options_form()
        for name, field in form.fields.items():
           add_argument_from_field(parser, name, field) 
    #parser.add_argument('--output', help='set output type', default='print')
    return parser

def add_argument_from_field(parser, name, field):
    """
    Call parser.add_argument with the appropriate parameters
    to add this django.forms.Field to the argparse.ArgumentParsers parser.
    """
    # set options name to lowercase variant, remember name for storage
    optname = name.lower()
    if field.required and field.initial is None: # positional argument
        argname = [optname]
    else: # optional argument
        argname = ["--"+optname]
        prefix = "-" + optname[0]
        if prefix not in parser._option_string_actions:
            argname.append("-"+optname[0])
    # determine help text from label, help_text, and default
    helpfields = [x for x in [field.label, field.help_text] if x]
    if field.initial is not None: helpfields.append("Default: {field.initial}".format(**locals()))
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
    parser.add_argument(*argname, help = help, default=field.initial, dest=name, **args)


_FIELD_MAP = {
    forms.IntegerField : int,
    forms.BooleanField : bool,
    }
def argument_type_from_field(field):
    """Get the proper python type to parse a command line option"""
    for (ftype, type) in _FIELD_MAP.iteritems():
        if isinstance(field, ftype): return type
    return str
