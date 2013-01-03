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
As much as possible, actions in the navigator are handled by calling actions
from amcat.script.actions.

This module contains helpful code for calling these actions from the website
"""


class ActionHandler(object):
    """
    An action handler handles creating the form and possibly running the action.
    Uses an object rather than a simple function because the return type is
    complex: what is the form? did the action run? what is the result?
    """
    def __init__(self, action, **context):
        self.action = action
        self.context = context

    def handle(self, request):
        """
        Handle the request, returns True if the request was a valid POST.
        self.form will contain the (bound) form, and self.result the result
        of running the action, or None if it was not run.
        """
        if request.POST:
            self.form = self.action.options_form(request.POST)

            if not self.form.is_valid():
                return False

            self.result =  self.action(self.form).run()
            return True
        else:
            self.form = self.action.get_empty_form(**self.context)
            self.result = None
            return False
