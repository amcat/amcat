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
"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.tools.model import AmcatModel

from django.db import models

import logging; log = logging.getLogger(__name__)

ALL = ["CodingRuleAction", "CodingRule"]

class CodingRuleAction(AmcatModel):
    """Model representing an action  """
    label = models.CharField(max_length=50)
    description = models.TextField()

    class Meta():
        db_table = 'codingruleactions'
        app_label = 'amcat'

class CodingRule(AmcatModel):
    """
    A CodingRule 
    """
    label = models.CharField(max_length=75)

    condition = models.TextField()
    field = models.ForeignKey("amcat.CodingSchemaField", null=True)
    action = models.ForeignKey("amcat.CodingRuleAction", null=True)

    codingschema = models.ForeignKey("amcat.CodingSchema", related_name='rules')

    class Meta():
        db_table = 'codingrules'
        app_label = 'amcat'

