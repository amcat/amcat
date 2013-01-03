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
Contains AmCAT specific rest fields.

See: http://django-rest-framework.org/api-guide/fields.html
"""

import json

from rest_framework.fields import Field 

class DatatablesEchoField(Field):
    """
    Supports the echo-feature which is required by datatables. See the
    documentation of datatables for more information:

      http://datatables.net/usage/server-side

    """
    def to_native(self, obj):
        dt_opts = self.context['request'].GET.get("datatables_options")

        try:
            dt_opts = json.loads(dt_opts)
        except (TypeError, ValueError) as e:
            return None

        # Try to return sEcho to prevent XSS attacks
        return dt_opts.get('sEcho')

