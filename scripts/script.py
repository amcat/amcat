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


class InvalidFormException(Exception):
    """ exception which is raised when the form contains one or more fields in error """
    def __init__(self, message, errors):
        Exception.__init__(self, message)
        self.errors = errors

    def getErrorDict(self):
        """returns the fields containing errors as dict, with the fieldname as key and the errors as value (in a list, there can be more than one)"""
        return dict([(k, [unicode(e) for e in v]) for k,v in self.errors.items()]) 
 
        
        
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
        if self.options_form == None:
            self.options = self._options_raw = None
        else:
            options = _validate_form(self.options_form, options, **kargs)
            self.options = options.cleaned_data
            self._options_raw = options
        
    def run(self, input=None):
        """Run is invoked with the input, which should be of type input_type,
        and should return a result of type output_type or raise an exception"""
        pass

        
        
    
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
        if isinstance(options, dict) or isinstance(options, QueryDict) or isinstance(options, MergeDict):
            options = options_form(options)
        else:
            if options is not None: kargs['options'] = options
            options = options_form(kargs)

    if not isinstance(options, options_form):
        raise ValueError("Provided options form class %s is not an instance of required options_form class %s" % (options.__class__, options_form.__class__))

    if not options.is_bound:
        raise ValueError("Cannot call %r script with unbound form" % self.__class__.__name__)

    if not options.is_valid():
        raise InvalidFormException("Invalid or missing options: %r" % options.errors, options.errors)

    return options
   
