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
from django.db.utils import IntegrityError
from amcat.models import CodedArticleStatus, STATUS_NOTSTARTED, STATUS_INPROGRESS, STATUS_COMPLETE, \
    STATUS_IRRELEVANT, CodedArticle

from amcat.tools import amcattest

class TestCodedArticle(amcattest.AmCATTestCase):
    def test_comments(self):
        """Can we set and read comments?"""
        from amcat.models import CodedArticle
        ca = amcattest.create_test_coded_article()
        self.assertIsNone(ca.comments)

        for offset in range(4563, 20000, 1000):
            s = "".join(unichr(offset + c) for c in range(12, 1000, 100))
            ca.comments = s
            ca.save()
            ca = CodedArticle.objects.get(pk=ca.id)
            self.assertEqual(ca.comments, s)

    def _get_coding_dict(self, sentence_id=None, field_id=None, intval=None, strval=None, start=None, end=None):
        return {
            "sentence_id" : sentence_id,
            "start" : start,
            "end" : end,
            "values" : [{
                "codingschemafield_id" : field_id,
                "intval" : intval,
                "strval" : strval
            }]
        }

    def test_replace_codings(self):
        schema, codebook, strf, intf, codef, _, _ = amcattest.create_test_schema_with_fields(isarticleschema=True)
        schema2, codebook2, strf2, intf2, codef2, _, _ = amcattest.create_test_schema_with_fields(isarticleschema=True)
        codingjob = amcattest.create_test_job(articleschema=schema, narticles=10)

        coded_article = CodedArticle.objects.get(article=codingjob.articleset.articles.all()[0], codingjob=codingjob)
        coded_article.replace_codings([self._get_coding_dict(intval=10, field_id=codef.id)])

        self.assertEqual(1, coded_article.codings.all().count())
        self.assertEqual(1, coded_article.codings.all()[0].values.all().count())
        coding = coded_article.codings.all()[0]
        value = coding.values.all()[0]
        self.assertEqual(coding.sentence, None)
        self.assertEqual(value.strval, None)
        self.assertEqual(value.intval, 10)
        self.assertEqual(value.field, codef)

        # Overwrite previous coding
        coded_article.replace_codings([self._get_coding_dict(intval=11, field_id=intf.id)])
        self.assertEqual(1, coded_article.codings.all().count())
        self.assertEqual(1, coded_article.codings.all()[0].values.all().count())
        coding = coded_article.codings.all()[0]
        value = coding.values.all()[0]
        self.assertEqual(coding.sentence, None)
        self.assertEqual(value.strval, None)
        self.assertEqual(value.intval, 11)
        self.assertEqual(value.field, intf)

        # Try to insert illigal values
        illval1 = self._get_coding_dict(intval=1, strval="a", field_id=intf.id)
        illval2 = self._get_coding_dict(field_id=intf.id)
        illval3 = self._get_coding_dict(intval=1)
        illval4 = self._get_coding_dict(intval=1, field_id=strf2.id)

        self.assertRaises(ValueError, coded_article.replace_codings, [illval1])
        self.assertRaises(ValueError, coded_article.replace_codings, [illval2])
        self.assertRaises(IntegrityError, coded_article.replace_codings, [illval3])
        self.assertRaises(ValueError, coded_article.replace_codings, [illval4])

        # Unspecified values default to None
        val = self._get_coding_dict(intval=1, field_id=intf.id)
        del val["values"][0]["strval"]
        coded_article.replace_codings([val])
        value = coded_article.codings.all()[0].values.all()[0]
        self.assertEqual(value.strval, None)
        self.assertEqual(value.intval, 1)

        val = self._get_coding_dict(strval="a", field_id=intf.id)
        del val["values"][0]["intval"]
        coded_article.replace_codings([val])
        value = coded_article.codings.all()[0].values.all()[0]
        self.assertEqual(value.strval, "a")
        self.assertEqual(value.intval, None)


class TestCodedArticleStatus(amcattest.AmCATTestCase):
    def test_status(self):
        """Is initial status 0? Can we set it?"""
        ca = amcattest.create_test_coded_article()
        self.assertEqual(ca.status.id, 0)
        self.assertEqual(ca.status, CodedArticleStatus.objects.get(pk=STATUS_NOTSTARTED))
        ca.set_status(STATUS_INPROGRESS)
        self.assertEqual(ca.status, CodedArticleStatus.objects.get(pk=1))
        ca.set_status(STATUS_COMPLETE)
        self.assertEqual(ca.status, CodedArticleStatus.objects.get(pk=2))
        ca.set_status(STATUS_IRRELEVANT)
        self.assertEqual(ca.status, CodedArticleStatus.objects.get(pk=9))
        ca.set_status(STATUS_NOTSTARTED)
        self.assertEqual(ca.status, CodedArticleStatus.objects.get(pk=0))


