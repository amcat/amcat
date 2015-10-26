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
from copy import copy
from itertools import chain, count
from operator import attrgetter
import logging
import collections
import uuid

from django.template.loader import get_template
from django.template import Context
from django.db import models, transaction
from django.db.utils import IntegrityError, DatabaseError
from django.core.exceptions import ValidationError
from django.template.defaultfilters import escape as escape_filter
from amcat.tools.djangotoolkit import bulk_insert_returning_ids

from amcat.tools.model import AmcatModel, PostgresNativeUUIDField
from amcat.tools import amcates
from amcat.models.authorisation import Role
from amcat.models.medium import Medium
from amcat.tools.toolkit import splitlist
from amcat.tools.tree import Tree
from amcat.tools.progress import ProgressMonitor

from amcat.tools.amcates import Result

log = logging.getLogger(__name__)

import re

WORD_RE = re.compile('[{L}{N}]+')  # {L} --> All (unicode) letters
# {N} --> All numbers


def word_len(txt):
    """Count words in `txt`

    @type txt: str or unicode"""
    if not txt: return 0  # Safe handling of txt=None
    return len(re.sub(WORD_RE, ' ', txt).split())


def unescape_em(txt):
    """
    @param txt: text to be unescaped
    @type txt: unicode
    """
    return (txt
            .replace("&lt;em&gt;", "<em>")
            .replace("&lt;/em&gt;", "</em>"))


class ArticleTree(Tree):
    @property
    def article(self):
        return self.obj

    def get_ids(self):
        return self.traverse(func=lambda t: t.obj.id)

    def get_html(self, active=None, articleset=None):
        """
        Returns tree represented as HTML.

        @param active: highlight this article (wrap in em-tags)
        @type active: amcat.models.Article

        @param articleset: for all articles in this tree which are also in this
                           articleset, created a hyperlink.
        @type articleset: amcat.models.ArticleSet
        @rtype: compiled Template object
        """
        articles = set()
        if articleset is not None:
            articles = articleset.articles.filter(id__in=self.get_ids())
            articles = set(articles.values_list("id", flat=True))

        context = Context(dict(locals(), tree=self))
        return get_template("amcat/article_tree_root.html").render(context)


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
                               db_index=True, blank=True, related_name="children")
    # Allow .parent to be set to an article that still needs saving
    # cf. https://www.caktusgroup.com/blog/2015/07/28/using-unsaved-related-models-sample-data-django-18/
    parent.allow_unsaved_instance_assignment = True
    
    project = models.ForeignKey("amcat.Project", db_index=True, related_name="articles")
    medium = models.ForeignKey(Medium, db_index=True)

    insertscript = models.CharField(blank=True, null=True, max_length=500)
    insertdate = models.DateTimeField(blank=True, null=True, auto_now_add=True)

    def __init__(self, *args, **kwargs):
        super(Article, self).__init__(*args, **kwargs)
        self._highlighted = False

    class Meta():
        db_table = 'articles'
        app_label = 'amcat'

    def highlight(self, query, escape=True, keep_em=True):
        """
        Highlight headline and text property by inserting HTML tags (em). You won't be able to
        call save() after calling this method.

        @param query: elastic query used for highlighting
        @type query: unicode

        @param escape: escape html entities in result
        @type escape: bool

        @param keep_em: has no effect if escape is False. Will unescape em tags, which
                        are used for highlighting.
        @type keep_em: bool
        """
        if self._highlighted: return
        self._highlighted = True

        highlighted = amcates.ES().highlight_article(self.id, query)

        if not highlighted:
            # No hits for this search query
            return

        self.text = highlighted.get("text", self.text)
        self.headline = highlighted.get("headline", self.headline)

        if escape:
            self.text = escape_filter(self.text)
            self.headline = escape_filter(self.headline)

            if keep_em:
                self.text = unescape_em(self.text)
                self.headline = unescape_em(self.headline)

        return highlighted

    @property
    def children(self):
        """Return a sequence of all child articles (eg reactions to a post)"""
        return Article.objects.filter(parent=self)

    def save(self, *args, **kwargs):
        if self._highlighted:
            raise ValueError("Cannot save a highlighted article.")

        if self.length is None:
            self.length = word_len(self.text)

        super(Article, self).save(*args, **kwargs)


    def words(self):
        """@return: a generator yielding all words in all sentences"""
        for sentence in self.sentences:
            for word in sentence.words:
                yield word

    def get_sentence(self, parnr, sentnr):
        """@return: a Sentence object with the given paragraph and sentence number"""
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
    def exists(cls, article_ids, batch_size=500):
        """
        Filters the given articleids to remove non-existing ids
        """
        for batch in splitlist(article_ids, itemsperbatch=batch_size):
            for aid in Article.objects.filter(pk__in=batch).values_list("pk", flat=True):
                yield aid

    @classmethod
    def create_articles(cls, articles, articleset=None, articlesets=None,
                        monitor=ProgressMonitor()):
        """
        Add the given articles to the database, the index, and the given set

        Duplicates are detected and have .duplicate, .id, and .uuid set (and are added to sets)
        Articles can have a .parent object set to another (unsaved) object in the set
        in which case the parent will be saved first
        
        @param articles: a collection of objects with the necessary properties (.headline etc)
        @param articleset(s): articleset object(s), specify either or none
        """
        cls._create_articles_per_layer(articles)
        if articlesets is None:
            articlesets = [articleset] if articleset else []

        es = amcates.ES()
        dupes, new = [], []
        for a in articles:
            if a.duplicate:
                dupes.append(a)
            else:
                a.es_dict.update(dict(sets=[aset.id for aset in articlesets],
                                      uuid=unicode(a.uuid), id=a.id))
                new.append(a)

        if new:
            es.bulk_insert([a.es_dict for a in new], batch_size=100)
            for aset in articlesets:
                aset.add_articles(new, add_to_index=False)
        if dupes:
            for aset in articlesets:
                aset.add_articles(dupes, add_to_index=True)
            
    @classmethod
    def _create_articles_per_layer(cls, articles):
        """Call _do_create_articles for each layer of the .parent tree"""
        while articles:
            to_save, todo = [], []
            for a in articles:
                # set parent_id from dupe if needed
                if a.parent and not a.parent_id:
                    if a.parent.id:
                        a.parent_id = a.parent.id
                    elif hasattr(a.parent, "duplicate"):
                        a.parent_id = a.parent.duplicate.id
                if (a.parent is None) or a.parent_id or a.parent.id:
                    to_save.append(a)
                else:
                    todo.append(a)
            if not to_save:
                raise ValueError("Parent cycle")
            cls._do_create_articles(to_save)
            articles = todo
    
    @classmethod
    def _do_create_articles(cls, articles):
        """Check duplicates and save the articles to db.
        Does *not* save to elastic or add to articlesets
        Assumes that if .parent is given, it has an id
        (because parent is part of hash)
        modifies all articles in place with .hash and either .duplicate or .id and .uuid
        """
        es = amcates.ES()
        dupe_values = {'uuid': {}, 'hash': {}}
        # Iterate over articles, remove duplicates within addendum and build dupe values dictionary 
        for a in articles:
            if a.id:
                raise ValueError("Specifying explicit article ID in save not allowed")
            if a.length is None:
                a.length = word_len(a.text) + word_len(a.headline) + word_len(a.byline)
            a.es_dict = amcates.get_article_dict(a)
            a.hash = a.es_dict['hash']
            a.duplicate = None # innocent until proven guilty
            for attr in dupe_values:
                val = getattr(a, attr)
                if val:
                    val = unicode(val)
                    if val in dupe_values[attr]:
                        a.duplicate = dupe_values[attr][val] # within-set duplicate
                    else:
                        dupe_values[attr][val] = a
        # for each duplicate indicator, query es and get existing articles
        for attr in dupe_values:
            values = dupe_values[attr]
            if values:
                results = es.query_all(filters={attr: values.keys()}, fields=["hash", "uuid"], score=False)
                for r in results:
                    a =values[getattr(r, attr)]
                    if a.hash != r.hash: 
                        raise ValueError("Cannot modify existing articles: {a.hash} != {r.hash}".format(**locals()))
                    if a.uuid and unicode(a.uuid) != unicode(r.uuid): # not part of hash
                        raise ValueError("Cannot modify existing articles: {a.uuid} != {r.uuid}".format(**locals()))
                    a.duplicate = r
                    a.id = r.id
                
        # now we can save the articles and set id
        to_insert = {}
        for a in articles:
            if not a.duplicate:
                if not a.uuid: a.uuid = uuid.uuid4()
                assert a.uuid not in to_insert
                to_insert[unicode(a.uuid)] = a
        if to_insert:
            for b in bulk_insert_returning_ids(to_insert.values(), fields=["uuid"]):
                to_insert[unicode(b.uuid)].id = b.pk
        return to_insert.values()

        
    def get_tree(self, include_parents=True, fields=("id",)):
        """
        Returns a deterministic (sorted by id) tree of articles, based on their parent
        property. It runs O(2n) database queries, where `n` depth of tree queries.

        @param include_parents: start at root of tree, instead of this node
        @type include_parents: bool

        @param fields:
        @type fields: tuple of string

        @rtype: ArticleTree
        """
        # Do we need to render the complete tree?
        if include_parents and self.parent and self.parent.id != self.id:
            return self.parent.get_tree(include_parents=True)

        children = self.children.order_by("id").only(*fields)
        return ArticleTree(self, [c.get_tree(include_parents=False) for c in children
                                  if c.id != self.id])

