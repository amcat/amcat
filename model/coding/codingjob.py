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
Model module containing Codingjobs

Coding Jobs are sets of articles assigned to users for manual annotation.
Each coding job has annotationschemas for articles and/or sentences. A coding
job can consists of multiple sets, which represent a set of articles assigned
to an individual coder. 
"""

from amcat.tools.model import AmcatModel

from amcat.model.coding.annotationschema import AnnotationSchema
from amcat.model.user import User
from amcat.model.project import Project

from django.db import models

import logging; log = logging.getLogger(__name__)
            
class CodingJob(AmcatModel):
    """
    Model class for table codingjobs. A Coding Job is a container of sets of articles
    assigned to coders in a project with a specified unit and article schema
    """

    id = models.AutoField(primary_key=True, db_column='codingjob_id')

    name = models.CharField(max_length=100)

    unitschema = models.ForeignKey(AnnotationSchema, related_name='+')
    articleschema = models.ForeignKey(AnnotationSchema, related_name='+')

    insertdate = models.DateTimeField(auto_now_add=True)
    insertuser = models.ForeignKey(User)

    project = models.ForeignKey(Project)

    def __unicode__(self):
        return self.name

    class Meta():
        db_table = 'codingjobs'
        app_label = 'amcat'


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodingJob(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create a dummy coding job?"""
        u = amcattest.create_test_user()
        p = amcattest.create_test_project()
        s = amcattest.create_test_schema()
        j = CodingJob.objects.create(project=p, unitschema=s, articleschema=s, insertuser=u)
        self.assertIsNotNone(j)
