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

from django.forms import BaseForm

class InvalidFormException(Exception):
    """ exception which is raised when the form contains one or more fields in error. 
    Uses an additional parameter with the Django form error object (form.errors)"""
    
    def __init__(self, message_or_form, errors=None):
	"""Create an exception signalling a validation problem with the form
	@param message_or_form: the invalid form object, or a message string
	@param errors: the errors, will be extracted from first argument if it is a form
	"""
	if isinstance(message_or_form, BaseForm):

	    message = "Invalid or missing options: %r" % message_or_form.errors
	    errors = message_or_form.errors
	else:
	    message = message_or_form
        Exception.__init__(self, message)
        self.errors = errors

    def getErrorDict(self):
        """Returns the fields containing errors as dict, with the fieldname as key
	and the errors as value (in a list, there can be more than one)"""
        return dict([(field, [unicode(e) for e in errorList]) for field, errorList in self.errors.items()]) 
 
def validate(form):
    """Validate the given form, raising an InvalidFormException if invalid"""
    if not form.is_valid():
	raise InvalidFormException(form)
