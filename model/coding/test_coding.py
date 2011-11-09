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
Test module to make sure that the amcat facilities for manual coding work
as expected. The tests on the individual model classes should test whether
they work separately. This tests whether the end-use of the classes taken
together works as intended (eg a sort of integration test).
"""


from amcat.tools import amcattest

from amcat.model.coding.codingjob import CodingJobSet

from amcat.model.coding.annotationschema import AnnotationSchema
from amcat.model.coding.annotationschemafield import AnnotationSchemaField
from amcat.model.coding.annotationschemafield import AnnotationSchemaFieldType

class TestCoding(amcattest.PolicyTestCase):

    def _getset(self):
        # create a coding job set with a sensible schema and some articles to 'code'
        schema = amcattest.create_test_schema()
        for i, (ftype, label) in enumerate([
                (AnnotationSchemaFieldType.objects.get(pk=1), "text"),
                (AnnotationSchemaFieldType.objects.get(pk=2), "number"),
                ]):
            AnnotationSchemaField.objects.create(annotationschema=schema,
                                                 fieldnr=i, fieldtype=ftype, fieldname=label)

        j = amcattest.create_test_job(articleschema=schema)
        s = amcattest.create_test_set(articles=10)
        return CodingJobSet.objects.create(codingjob=j, articleset=s, coder=j.insertuser)
        
    def test_test(self):
        """Test whether value assignment and retrieval works"""
        s = self._getset()
        



        

