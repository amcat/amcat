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
from django.core.exceptions import ValidationError, PermissionDenied
from django.template.defaultfilters import escape as escape_filter
from amcat.tools.djangotoolkit import bulk_insert_returning_ids

from amcat.tools.model import AmcatModel, PostgresNativeUUIDField
from amcat.tools import amcates
from amcat.models.authorisation import Role
from amcat.models.medium import Medium
from amcat.tools.toolkit import splitlist
from amcat.tools.tree import Tree
from amcat.tools.progress import ProgressMonitor
from amcat.models.authorisation import ROLE_PROJECT_READER

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
    length = models.IntegerField(blank=True, null=True)
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
    def create_articles(cls, articles, articleset=None, articlesets=None, deduplicate=True,
                        monitor=ProgressMonitor()):
        """
        Add the given articles to the database, the index, and the given set

        Duplicates are detected and have .duplicate, .id, and .uuid set (and are added to sets)
        Articles can have a .parent object set to another (unsaved) object in the set
        in which case the parent will be saved first
        
        @param articles: a collection of objects with the necessary properties (.headline etc)
        @param articleset(s): articleset object(s), specify either or none
        """
        _check_index(articles)
        cls._create_articles_per_layer(articles, deduplicate=deduplicate)
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
    def _create_articles_per_layer(cls, articles, deduplicate=True):
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
            cls._do_create_articles(to_save, deduplicate=deduplicate)
            articles = todo
    
    @classmethod
    def _do_create_articles(cls, articles, deduplicate=True):
        """Check duplicates and save the articles to db.
        Does *not* save to elastic or add to articlesets
        Assumes that if .parent is given, it has an id
        (because parent is part of hash)
        modifies all articles in place with .hash, .id, .uuid, and .duplicate (None or Article)
        """
        es = amcates.ES()

        uuids = {} # {uuid : article}
        hashes = collections.defaultdict(list) # {hash: articles}
        
        # Iterate over articles, mark duplicates within addendum and build uuids/hashes dictionaries
        for a in articles:
            if a.id:
                raise ValueError("Specifying explicit article ID in save not allowed")
            a.es_dict = amcates.get_article_dict(a)
            a.hash = a.es_dict['hash']
            if not hasattr(a, 'uuid'): a.uuid = None
            a.duplicate, a.internal_duplicate = None, None # innocent until proven guilty
            if not deduplicate:
                continue

            if a.uuid:
                uuid = unicode(a.uuid)
                if uuid in uuids:
                    raise ValueError("Duplicate UUID in article upload")
                uuids[uuid] = a
            else: # articles with explicit uuid cannot be deduplicated on hash
                hashes[a.hash].append(a)
            
        def _set_dupe(dupe, orig):
            dupe.duplicate = orig
            dupe.id = orig.id
            dupe.uuid = orig.uuid

        # check dupes based on hash
        if hashes:
            results = es.query_all(filters={'hash': hashes.keys()},
                                   fields=["hash", "uuid"], score=False)
            for orig in results:
                for dupe in hashes[orig.hash]:
                    _set_dupe(dupe, orig)

        # check dupes based on uuid (if any are given)
        if uuids:
            # uuid is not stored correctly in amcat.nl as of 3.4, so use db to query uuids
            aids = {id: unicode(uuid) for (id, uuid) in
                    Article.objects.filter(uuid__in=uuids.keys()).values_list("pk", "uuid")}
            if aids:
                results = es.query_all(filters={'id': aids.keys()}, fields=["hash"], score=False)
                for orig in results:
                    orig.uuid = unicode(aids[orig.id])
                    dupe = uuids[orig.uuid]
                    if dupe.hash != orig.hash:
                        amcates.get_article_dict(Article.objects.get(pk=orig.id))
                        raise ValueError("Cannot modify existing article for uuid={orig.uuid}: {orig.hash} != {dupe.hash}".format(**locals()))
                    _set_dupe(dupe, orig)
                
        # now we can save the articles and set id
        to_insert = [a for a in articles if not a.duplicate]
        result = bulk_insert_returning_ids(to_insert)
        if len(to_insert) == 0:
            return []
        for a, inserted in zip(to_insert, result):
            a.id = inserted.id
        return to_insert

        
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

def _check_index(articles):
    # since dupe checking is done using ES, things go wrong if articles are missing in ES.
    # the ones with uuid we can refresh, the others will just be added as dupe
    es = amcates.ES()
    uuids = {a.uuid for a in articles if a.uuid}
    aids = list(Article.objects.filter(uuid__in=uuids).values_list("pk", flat=True))
    in_index = set(es.query_ids(filters={"ids":aids}))
    missing = set(aids) - in_index
    if missing:
        log.info("Adding {} articles to index".format(len(missing)))
        es.add_articles(missing)
    es.flush() 
            

def _check_read_access(user, aids):
    """Raises PermissionDenied if the user does not have full read access on all given articles"""
    # get article set memberships
    from amcat.models import ArticleSet, Project

    sets = list(ArticleSet.articles.through.objects.filter(article_id__in=aids).values_list("articleset_id", "article_id"))
    setids = {setid for (setid, aid) in sets}
    
    # get project memberships
    ok_sets = set()
    project_cache = {} # pid : True / False
    def project_ok(pid):
        if pid not in project_cache:
            project_cache[pid] = (Project.objects.get(pk=pid).get_role_id(user) >= ROLE_PROJECT_READER)
        return project_cache[pid]

    asets = [ArticleSet.objects.filter(pk__in=setids).values_list("pk", "project_id"),
             Project.articlesets.through.objects.filter(articleset_id__in=setids)
             .values_list("articleset_id", "project_id")]
    
    for aset in asets:
        for sid, pid in aset:
            if project_ok(pid):
                ok_sets.add(sid)


    ok_articles = set()
    for sid, aid in sets:
        if sid in ok_sets:
            ok_articles.add(aid)
    aids = {aid for (setid, aid) in sets}
    if aids - ok_articles:
        logging.info("Permission denied for {user}, articles {}".format(aids - ok_articles, **locals()))
        raise PermissionDenied("User does not have full read access on (some) of the selected articles")
    
    
    
        

