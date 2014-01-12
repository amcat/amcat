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
Model module containing the Article class representing documents in the
articles database table.
"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.tools.model import AmcatModel, PostgresNativeUUIDField
from amcat.tools import amcates
from amcat.models.authorisation import Role
from amcat.models.medium import Medium

from django.db import models, transaction
from django.db.utils import IntegrityError, DatabaseError
from django.core.exceptions import ValidationError

import logging;

log = logging.getLogger(__name__)

import re

WORD_RE = re.compile('[{L}{N}]+') # {L} --> All (unicode) letters
                                  # {N} --> All numbers

def word_len(txt):
    """Count words in `txt`

    @type txt: str or unicode"""
    if not txt: return 0 # Safe handling of txt=None
    return len(re.sub(WORD_RE, ' ', txt).split())

class Article(AmcatModel):
    """
    Class representing a newspaper article
    """
    __label__ = 'headline'

    id = models.AutoField(primary_key=True, db_column="article_id")

    date = models.DateTimeField(db_index=True)
    section = models.CharField(blank=True, null=True, max_length=500)
    pagenr = models.IntegerField(blank=True, null=True)
    headline = models.TextField()
    byline = models.TextField(blank=True, null=True)
    length = models.IntegerField(blank=True)
    metastring = models.TextField(null=True, blank=True)
    url = models.TextField(null=True, blank=True, db_index=True, max_length=750)
    externalid = models.IntegerField(blank=True, null=True)
    author = models.TextField(blank=True, null=True, max_length=100)
    addressee = models.TextField(blank=True, null=True, max_length=100)
    uuid = PostgresNativeUUIDField(db_index=True, unique=True)
    
    #sets = models.ManyToManyField("amcat.Set", db_table="sets_articles")

    text = models.TextField()

    parent = models.ForeignKey("self", null=True, db_column="parent_article_id",
                               db_index=True, blank=True)
    project = models.ForeignKey("amcat.Project", db_index=True, related_name="articles")
    medium = models.ForeignKey(Medium, db_index=True)

    class Meta():
        db_table = 'articles'
        app_label = 'amcat'

    @property
    def children(self):
        """Return a sequence of all child articles (eg reactions to a post)"""
        return Article.objects.filter(parent=self)

    def save(self, *args, **kwargs):
        if self.length is None:
            self.length = word_len(self.text) + word_len(self.headline) + word_len(self.byline)

        super(Article, self).save(*args, **kwargs)


    def words(self):
        "@return: a generator yielding all words in all sentences"
        for sentence in self.sentences:
            for word in sentence.words:
                yield word

    def get_sentence(self, parnr, sentnr):
        "@return: a Sentence object with the given paragraph and sentence number"
        for s in self.sentences:
            if s.parnr == parnr and s.sentnr == sentnr:
                return s

    def getSentence(self, parnr, sentnr):
        return self.get_sentence(parnr, sentnr)

    ## Auth ##
    def can_read(self, user):
        if user.is_superuser:
            return True

        # Check default role on project
        read_meta = Role.objects.get(label='metareader', projectlevel=True)
        if self.project.guest_role.id >= read_meta.id:
            return True

        # Check users role on project
        if user.projectrole_set.filter(project__articles__article=self, role__id__gt=read_meta.id):
            return True

        return False

    def __repr__(self):
        return "<Article %s: %r>" % (self.id, self.headline)

    @classmethod
    def create_articles(cls, articles, articleset=None, check_duplicate=True):
        """
        Add the given articles to the database, the index, and the given set

        Article objects can contain a 'custom' nested_articles attribute. In that case,
        this should be a list of article-like objects that will also be saved, and will
        have the .parent set to the containing article
        
        @param articles: a collection of objects with the necessary properties (.headline etc)
        @param articleset: an articleset object
        @param check_duplicate: if True, duplicates are not added to the database or index
        (the 'existing' article *is* added to the set.
        """
        # TODO: test parent logic (esp. together with hash/dupes)
        es = amcates.ES()

        # add dict (+hash) as property on articles so we know who is who
        sets = [articleset.id] if articleset else None
        for a in articles:
            a.es_dict = amcates.get_article_dict(a, sets=sets)

        if check_duplicate:
            hashes = [a.es_dict['hash'] for a in articles]
            results =es.query(filters={'hashes' : hashes}, fields=["hash", "sets"], score=False) 
            dupes = {r.hash : r for r in results}
        else:
            dupes = {}

        # add all non-dupes to the db, needed actions        
        add_to_set = set() # duplicate article ids to add to set
        add_new_to_set = set() # new article ids to add to set
        add_to_index = [] # es_dicts to add to index
        result = [] # return result
        errors = [] # return errors
        for a in articles:
            dupe = dupes.get(a.es_dict['hash'], None)
            if dupe:
                a.duplicate_of = dupe.id
                if articleset and not (dupe.sets and articleset.id in dupe.sets):
                    add_to_set.add(dupe.id)
            else:
                if a.parent:
                    a.parent_id = a.parent.duplicate_of if hasattr(a.parent, 'duplicate_of') else a.parent.id
                sid = transaction.savepoint()
                try:
                    sid = transaction.savepoint()
                    a.save()
                    transaction.savepoint_commit(sid)
                except (IntegrityError, ValidationError, DatabaseError) as e:
                    log.warning(str(e))
                    transaction.savepoint_rollback(sid)
                    errors.append(e)
                    continue
                result.append(a)
                a.es_dict['id'] = a.pk
                add_to_index.append(a.es_dict)
                add_new_to_set.add(a.pk)

        log.info("Considered {} articles: {} saved to db, {} new to add to index, {} duplicates to add to set"
                 .format(len(articles), len(add_new_to_set), len(add_to_index), len(add_to_set)))

        # add to index
        if add_to_index:
            es.bulk_insert(add_to_index)
                
        if articleset:
            # add to articleset (db and index)
            articleset.add_articles(add_to_set | add_new_to_set, add_to_index=False)
            es.add_to_set(articleset.id, add_to_set)

        return result, errors

    @classmethod
    def ordered_save(cls, articles, *args, **kwargs):
        """Figures out parent-child relationships, saves parent first
        @param articles: a collection of unsaved articles
        @param articleset: an articleset object
        @param check_duplicate: if True, duplicates are not added to the database or index
        """
        index = {a.text: a for a in articles if a}
        articles, errors = cls.create_articles(articles, *args, **kwargs)
        for a in articles:
            parent = index[a.text].parent
            for b in articles:
                if parent and b.text == parent.text:
                    a.parent = b
                    a.save()
        return articles, errors
            
            

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestArticle(amcattest.AmCATTestCase):
    
    @amcattest.use_elastic
    def test_create(self):
        """Can we create/store/index an article object?"""
        a = amcattest.create_test_article(create=False, date='2010-12-31', headline=u'\ua000abcd\u07b4')
        Article.create_articles([a])
        db_a = Article.objects.get(pk=a.id)
        amcates.ES().flush()
        es_a = list(amcates.ES().query(filters={'ids': [a.id]}, fields=["date", "headline"]))[0]
        self.assertEqual(a.headline, db_a.headline)
        self.assertEqual(a.headline, es_a.headline)
        self.assertEqual('2010-12-31T00:00:00', db_a.date.isoformat())
        self.assertEqual('2010-12-31T00:00:00', es_a.date.isoformat())
        

    @amcattest.use_elastic
    def test_deduplication(self):
        """Does deduplication work as it is supposed to?"""
        art = dict(headline="test", byline="test", date='2001-01-01',
                   medium=amcattest.create_test_medium(),
                   project=amcattest.create_test_project(),
                   )
        
        a1 = amcattest.create_test_article(**art)
        def q(**filters):
            amcates.ES().flush()
            return set(amcates.ES().query_ids(filters=filters))
        self.assertEqual(q(mediumid=art['medium']), {a1.id})

        # duplicate articles should not be added
        a2 = amcattest.create_test_article(check_duplicate=True,**art)
        self.assertFalse(Article.objects.filter(pk=a2.id).exists())
        self.assertEqual(a2.duplicate_of, a1.id)
        self.assertEqual(q(mediumid=art['medium']), {a1.id})

        # however, if an articleset is given the 'existing' article
        # should be added to that set
        s1 = amcattest.create_test_set()
        a3 = amcattest.create_test_article(check_duplicate=True,articleset=s1, **art)
        
        self.assertFalse(Article.objects.filter(pk=a2.id).exists())
        self.assertEqual(a3.duplicate_of, a1.id)
        self.assertEqual(q(mediumid=art['medium']), {a1.id})
        self.assertEqual(set(s1.get_article_ids()), {a1.id})
        self.assertEqual(q(sets=s1.id), {a1.id})

        # can we suppress duplicate checking?
        a4 = amcattest.create_test_article(check_duplicate=False, **art)
        self.assertTrue(Article.objects.filter(pk=a4.id).exists())
        self.assertFalse(hasattr(a4, 'duplicate_of'))
        self.assertIn(a4.id, q(mediumid=art['medium']))
        
        
    def test_unicode_word_len(self):
        """Does the word counter eat unicode??"""
        u = u'Kim says: \u07c4\u07d0\u07f0\u07cb\u07f9'
        self.assertEqual(word_len(u), 3)

        b = b'Kim did not say: \xe3\xe3k'
        self.assertEqual(word_len(b), 5)
        
    @amcattest.use_elastic
    def test_unicode(self):
        """Test unicode headlines"""
        for offset in range(1, 10000, 1000):
            s = "".join(unichr(offset + c) for c in range(1, 1000, 100))
            a = amcattest.create_test_article(headline=s)
            self.assertIsInstance(a.headline, unicode)
            self.assertEqual(a.headline, s)

    @amcattest.use_elastic
    def test_medium_name(self):
        m = amcattest.create_test_medium(name="de testkrant")
        a = amcattest.create_test_article(medium=m)
        r = amcates.ES().query(filters={"id" : a.id}, fields=["medium"])
        print(r)
                                                             
