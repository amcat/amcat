"""
Interface definition and general functionality for amcat Scripts.

A Script is a generic "pluggable" functional element that can be
called from e.g. the Django site, as a standalone web interface, or as
a command line script.

Three subclasses of Script are also defined:
SearchScript takes no input and returns a Table or ArticleList;
Processor takes a Table or ArticleList as input and has flexible
output; and ArticleImporter takes a string as input and has a
(sequence of) (not yet saved) Articles as output. These subclasses
can be moved to more suitable locations in the future
"""

from django import forms

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
        options = _validate_form(self.options_form, options, **kargs)
        self.options = options.cleaned_data
        self._options_raw = options
        
    
    def run(self, input=None):
        """Run is invoked with the input, which should be of type input_type,
        and should return a result of type output_type or raise an exception"""
        pass

    @classmethod
    def run_cli(cls):
        """Handle command line interface invocation of this script"""
        parser = argument_parser_from_script(cls)
        args = parser.parse_args()
        instance = cls(args.__dict__)
        instance.run(None)
        # TODO: handle input and output in a sensible manner!
    
def _validate_form(options_form, options, **kargs):
    """Check whether a filled in form is valid given the form requirement

    If options is not given or is not a django form, attempt to create a bound options_form
    by calling options_form with either the options (if it is a dict) or the kargs dict.

    Checks whether the options form given or thus created is bound and valid, raising
    a ValueError if not
    
    @type options_form: django.forms.Form
    @param options_form: The Form to validate against, or None if optional
    @param options: Either the filled-in options form, or a dict containing options with which
                    to create a bound 'options_form'
    @param kargs: The options with which to create a bound 'options_form'
    @return: The validated options form
    """
    if not isinstance(options, forms.Form):
        if isinstance(options, dict):
            options = options_form(options)
        else:
            if options is not None: kargs['options'] = options
            options = options_form(kargs)
    if not isinstance(options, options_form):
        raise ValueError("Provided options form class %s is not an instance of required options_form class %s" % (options.__class__, options_form.__class__))
    if not options.is_bound:
        raise ValueError("Cannot call %r script with unbound form" % self.__class__.__name__)
    if not options.is_valid():
        raise ValueError("Invalid or missing options: %r" % options.errors)
    return options
   

###############################################################
##         Aux method for CLI invocation                     ##
###############################################################

import argparse

def argument_parser_from_script(script_class):
    """Create an argparse.ArgumentParser from a Script class object"""
    parser = argparse.ArgumentParser(description=script_class.__doc__)
    used_prefixes = set("-h") # keep track of -X options used; -h -> help
    if script_class.options_form:
        form = script_class.options_form()
        for name, field in form.fields.items():
           add_argument_from_field(parser, name, field) 
    return parser

def add_argument_from_field(parser, name, field):
    """
    Call parser.add_argument with the appropriate parameters
    to add this django.forms.Field to the argparse.ArgumentParsers parser.
    """
    name = name.lower()
    if field.required and not field.initial: # positional argument
        argname = [name]
    else: # optional argument
        argname = ["--"+name]
        prefix = "-" + name[0]
        if prefix not in parser._option_string_actions:
            argname.append("-"+name[0])
    # determine help text from label, help_text, and default
    helpfields = [x for x in [field.label, field.help_text] if x]
    if field.initial is not None: helpfields.append("Default: %s" % field.initial)
    help = ". ".join(helpfields)
    # set type OR action_const as extra arguments depending on type
    args = {} # flexible parameters to add_argument
    if isinstance(field, forms.BooleanField) and field.initial is not None:
        args["action"] = "store_const"
        args["const"] = not field.initial
    else:
        args["type"] = argument_type_from_field(field)
    parser.add_argument(*argname, help = help, default=field.initial, **args)


_FIELD_MAP = {
    forms.IntegerField : int,
    forms.BooleanField : bool,
    }
def argument_type_from_field(field):
    """Get the proper python type to parse a command line option"""
    for (ftype, type) in _FIELD_MAP.iteritems():
        if isinstance(field, ftype): return type
    return str
