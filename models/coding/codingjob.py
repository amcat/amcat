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

Coding Jobs are sets of articles assigned to users for manual coding.
Each coding job has codingschemas for articles and/or sentences.
"""

from amcat.tools.model import AmcatModel
from amcat.tools.caching import set_cache

from amcat.models.coding.codingschema import CodingSchema
from amcat.models.user import User
from amcat.models.project import Project
from amcat.models.articleset import ArticleSet



from django.db import models

import logging; log = logging.getLogger(__name__)
            
class CodingJob(AmcatModel):
    """
    Model class for table codingjobs. A Coding Job is a container of sets of articles
    assigned to coders in a project with a specified unit and article schema
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='codingjob_id')
    project = models.ForeignKey(Project)

    name = models.CharField(max_length=100)

    unitschema = models.ForeignKey(CodingSchema, related_name='codingjobs_unit')
    articleschema = models.ForeignKey(CodingSchema, related_name='codingjobs_article')

    insertdate = models.DateTimeField(auto_now_add=True)
    insertuser = models.ForeignKey(User, related_name="+")

    coder = models.ForeignKey(User)
    articleset = models.ForeignKey(ArticleSet, related_name="+")
    
    class Meta():
        db_table = 'codingjobs'
        app_label = 'amcat'


    def get_codings(self):
        """Return a sequence of codings with pre-fetched values"""
        # late import to prevent cycles
        from amcat.models.coding.coding import CodingValue
        
        q = CodingValue.objects.filter(coding__codingjob__exact=self)
        q = q.select_related("field__fieldtype", "value__strval", "value__intval", "coding")
        q = q.order_by("coding", 'field__fieldnr')
        # possible optimzation: use running values list because of sort order
        values_per_coding = {} # coding : [(field, value), ...]
        for val in q:
            values_per_coding.setdefault(val.coding, []).append((val.field,  val.value))
        for coding, values in values_per_coding.iteritems():
            set_cache(coding, coding.get_values.__name__, values)
            yield coding


        
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodingJob(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create a coding job with articles?"""
        p = amcattest.create_test_project()
        j = amcattest.create_test_job(project=p)
        self.assertIsNotNone(j)
        self.assertEqual(j.project, Project.objects.get(pk=p.id))
        j.articleset.add(amcattest.create_test_article())
        j.articleset.add(amcattest.create_test_article())
        j.articleset.add(amcattest.create_test_article())
        self.assertEqual(1+3, len(j.articleset.articles.all()))
        
        
        
        
