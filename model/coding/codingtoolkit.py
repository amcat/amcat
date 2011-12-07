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
Convenience functions to extract information about codings
"""

from __future__ import unicode_literals, print_function, absolute_import

from functools import partial

from amcat.model.coding.codingjob import CodingJobSet
from amcat.model.coding.coding import Coding, STATUS_COMPLETE
from amcat.model.coding.codedarticle import CodedArticle
from amcat.model.coding.codingschemafield import CodingSchemaField
from amcat.model.coding.codingschemafield import CodingSchemaFieldType

from amcat.tools.table.table3 import ObjectTable

def get_table_sets_per_user(users):
    """Return a table of all sets per user

    Columns: ids, jobname, coder, issuer, issuedate, #articles, #completed, #inprogress
    """
    try: iter(users)
    except TypeError: users = [users]
    result = ObjectTable(rows = list(CodingJobSet.objects.filter(coder__in=users)))
    result.addColumn("id")
    result.addColumn("codingjob")
    result.addColumn("coder")
    result.addColumn(lambda s: s.codingjob.insertuser, "insertuser")
    result.addColumn(lambda s :s.codingjob.insertdate, "insertdate")
    result.addColumn(lambda s :s.articleset.articles.count(), "narticles")
    result.addColumn(lambda s :s.codings.filter(sentence=None, status=2).count(),
                     "ncomplete")
    return result

def get_article_coding(cjset, article):
    """Find the 'article coding' for the given article"""
    result = cjset.codings.filter(article=article, sentence=None)
    assert len(result) <= 1
    if result: return result[0]

def get_coded_articles(cjsets):
    """Return a sequence of CodedArticle objects"""
    try: iter(cjsets)
    except TypeError: cjsets = [cjsets]
    for cjset in cjsets:
        for article in cjset.articleset.articles.all():
            yield CodedArticle(cjset, article)

def get_table_articles_per_set(cjsets):
    """Return a table of all articles in a cjset with status

    Columns: set, coder, article, articlemeta, status, comments
    """
    result = ObjectTable(rows = list(get_coded_articles(cjsets)))
    result.addColumn(lambda a: a.codingjobset.codingjob, "codingjob")
    result.addColumn(lambda a: a.codingjobset.coder, "coder")
    result.addColumn(lambda a: a.article.id, "articleid")
    result.addColumn(lambda a: a.article.headline, "headline")
    result.addColumn(lambda a: a.article.date, "date")
    result.addColumn(lambda a: a.article.medium, "medium")
    result.addColumn(lambda a: a.coding and a.coding.status, "status")
    result.addColumn(lambda a: a.coding and a.coding.comments, "comments")
    return result

def get_value(field, coding):
    """Return the (deserialized) value for field in this coding"""
    return dict(coding.get_values()).get(field)

def get_table_sentence_codings_article(codedarticle):
    """Return a table of sentence codings x fields

    The cells contain domain (deserialized) objects
    """
    result = ObjectTable(rows = list(codedarticle.sentence_codings))
    for field in codedarticle.codingjobset.codingjob.unitschema.fields.all():
        result.addColumn(partial(get_value, field), field.label)
    return result


        
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodingToolkit(amcattest.PolicyTestCase):

    def setUp(self):
        from amcat.model.coding.coding import CodingValue
        # create a coding job set with a sensible schema and some articles to 'code'
        self.schema = amcattest.create_test_schema()
        self.codebook = amcattest.create_test_codebook()
        self.code = amcattest.create_test_code(label="CODED")
        self.codebook.add_code(self.code)
        

        texttype = CodingSchemaFieldType.objects.get(pk=1)
        inttype = CodingSchemaFieldType.objects.get(pk=2)
        codetype = CodingSchemaFieldType.objects.get(pk=5)

        create = CodingSchemaField.objects.create
        self.textfield = create(codingschema=self.schema, fieldnr=1, fieldtype=texttype, 
                                label="Text")
        self.intfield = create(codingschema=self.schema,  fieldnr=2, fieldtype=inttype, 
                               label="Number")
        self.codefield = create(codingschema=self.schema, fieldnr=3, fieldtype=codetype, 
                                label="Code", codebook=self.codebook)

        self.users = [amcattest.create_test_user() for _x in range(2)]
        self.jobs = [amcattest.create_test_job(articleschema=self.schema, unitschema=self.schema)
                     for i in range(2)]
        self.asets = [amcattest.create_test_set(articles=2 * (i+1)) for i in range(5)]

        self.cjsets = []
        self.articles = []
        for a in self.asets:
            self.articles += list(a.articles.all())
        for (job, aset, user) in zip([0, 0, 0, 1, 1],
                                     [0, 1, 2, 3, 4],
                                     [0, 0, 0, 0, 1]):
            
            cjset = CodingJobSet.objects.create(codingjob=self.jobs[job],
                                                articleset=self.asets[aset],
                                                coder=self.users[user])
            self.cjsets += [cjset]

        self.an1 = Coding.objects.create(codingjobset=self.cjsets[0], article=self.articles[0])
        self.an2 = Coding.objects.create(codingjobset=self.cjsets[0], article=self.articles[1])
        self.an2.set_status(STATUS_COMPLETE)
        self.an2.comments = 'Makkie!'
        self.an2.save()

        sent = amcattest.create_test_sentence()
        self.sa1 = Coding.objects.create(codingjobset=self.cjsets[0], article=self.articles[0], 
                                             sentence=sent)
        self.sa2 = Coding.objects.create(codingjobset=self.cjsets[0], article=self.articles[0], 
                                             sentence=sent)
        create = CodingValue.objects.create
        create(coding=self.sa1, field=self.intfield, intval=1)
        create(coding=self.sa1, field=self.textfield, strval="bla")
        create(coding=self.sa2, field=self.textfield, strval="blx")
        create(coding=self.sa1, field=self.codefield, intval=self.code.id)

        
        
    def test_general(self):
        """Test whether the setUp works"""
        self.assertEqual(self.cjsets[0].coder, self.users[0])

        
    def test_table_codings(self):
        """Is the codings table correct?"""
        ca = CodedArticle(self.an1)
        t = get_table_sentence_codings_article(ca)
        self.assertIsNotNone(t)
        #print(t.output())
        aslist = [tuple(r) for r in t]
        self.assertEqual(aslist, [('bla', 1, self.code), ('blx', None, None)])
        
    def test_table_articles_per_set(self):
        """Is the articles per set table correct?"""
        t = get_table_articles_per_set([self.cjsets[i] for i in [0, 1]])
        #from amcat.tools.table import tableoutput; print; print(tableoutput.table2unicode(t))
        self.assertEqual([row.codingjob for row in t], [self.jobs[i] for i in [0] * 6])
        self.assertEqual([(row.status and row.status.id) for row in t], [0, 2]+[None]*4)
        

    def test_get_coded_articles(self):
        """Test the get_coded_articles function"""
        result = list(get_coded_articles(self.cjsets[i] for i in [0, 1]))
        sets = [self.cjsets[i] for i in (0, 0, 1, 1, 1, 1)]
        articles = [self.articles[i] for i in range(6)]
        codings = [self.an1, self.an2] + [None]*4
        self.assertEqual(len(result), len(sets))
        for result, aset, article, coding in zip(result, sets, articles, codings):
            ca = CodedArticle(aset, article)
            self.assertEqual(ca, result)
            self.assertEqual(coding, result.coding)


    def test_get_article_coding(self):
        """Correctly identify the article coding for an article"""
        self.assertEqual(self.an1, get_article_coding(self.cjsets[0], self.articles[0]))
        self.assertIsNone(get_article_coding(self.cjsets[1], self.articles[2]))
        
    def test_table_sets_per_user(self):
        """Is the sets per user table correct"""
        t = get_table_sets_per_user(self.users[0])
        #from amcat.tools.table.tableoutput import table2unicode; print(table2unicode(t))
        self.assertEqual([row.codingjob for row in t], [self.jobs[i] for i in [0, 0, 0, 1]])
        self.assertEqual([row.narticles for row in t], [2, 4, 6, 8])
        
        self.assertIsNotNone(t)

        
    def test_nqueries_table_sentence_codings(self):
        """Check for efficient retrieval of codings"""
        from amcat.model.coding.coding import CodingValue
        from amcat.tools.djangotoolkit import list_queries
        ca = CodedArticle(self.an1)

        # create 1000 sentence annotations
        for i in range(1):
            sent = amcattest.create_test_sentence()
            sa = Coding.objects.create(codingjobset=self.cjsets[0], article=self.articles[0], 
                                       sentence=sent)
            CodingValue.objects.create(coding=sa, field=self.intfield, intval=i)
        
        with list_queries() as l:
            t = get_table_sentence_codings_article(ca)
            t.output() # force getting all values
	#query_list_to_table(l, output=print, maxqlen=190)
        self.assertTrue(len(l) < 30, "Retrieving table used %i queries" % len(l))

        
