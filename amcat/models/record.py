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

"""ORM Module annotation-event records"""

from __future__ import print_function, absolute_import

from amcat.tools.model import AmcatModel
from django.contrib.auth.models import User

from django.db import models

class Record(AmcatModel):
    """Model for records.

    """
    __label__ = 'record'
    
    id = models.AutoField(primary_key=True, db_column="record_id")
    category = models.CharField(max_length=200)
    event_type = models.CharField(max_length=200)
    target_id = models.IntegerField()
    ts = models.DateTimeField()
    article = models.ForeignKey("amcat.Article", null=True)
    codingjob = models.ForeignKey("amcat.CodingJob", null=True)
    user = models.ForeignKey(User, null=True)

    class Meta():
        db_table = 'records'
        app_label = 'amcat'