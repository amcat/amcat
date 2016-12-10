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
import collections
import functools
import iso8601
import json
import re
import logging

from typing import Dict, Any, Union
from typing import List, Sequence, Set


import datetime
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, connection
from django.template.defaultfilters import escape as escape_filter
from django_hash_field import HashField
from psycopg2._json import Json

from amcat.models.authorisation import ROLE_PROJECT_READER
from amcat.models.authorisation import Role
from amcat.tools import amcates
from amcat.tools.djangotoolkit import bulk_insert_returning_ids
from amcat.tools.model import AmcatModel
from amcat.tools.progress import NullMonitor
from amcat.tools.toolkit import splitlist

from amcat.tools.amcates import get_property_primitive_type, is_valid_property_name

log = logging.getLogger(__name__)


WORD_RE_STRING = re.compile('[{L}{N}]+')  # {L} --> All letters
WORD_RE_BYTES = re.compile(b'[{L}{N}]+')  # {L} --> All letters
                                          # {N} --> All numbers

USED_PROPERTY_SQL = "SELECT DISTINCT jsonb_object_keys(properties) FROM articles WHERE article_id in ({});"

def word_len(txt):
    """Count words in `txt`

    @type txt: str"""
    if not txt: return 0  # Safe handling of txt=None
    word_re = WORD_RE_STRING if isinstance(txt, str) else WORD_RE_BYTES
    return len(re.sub(word_re, ' ', txt).split())


def unescape_em(txt):
    """
    @param txt: text to be unescaped
    @type txt: str
    """
    return (txt
            .replace("&lt;em&gt;", "<em>")
            .replace("&lt;/em&gt;", "</em>"))


def get_used_properties(articles: Union[Set[int], Sequence[int]]) -> Set[str]:
    # Don't accidentally pass strings (SQL injections and all)
    assert all(isinstance(v, int) for v in articles)

    # No articles given, no properties used :)
    if not articles:
        return set()

    # Query postgres for used properties
    ids = ",".join(map(str, articles))
    with connection.cursor() as cursor:
        cursor.execute(USED_PROPERTY_SQL.format(ids))
        properties = cursor.fetchall()
    return {row[0] for row in properties}


EMPTY = object()


class DateTimeEncoder(json.JSONEncoder):
    """Datetime aware JSON encoder. Credits: http://stackoverflow.com/a/27058505/478503"""
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        elif isinstance(o, datetime.date):
            return datetime.datetime(o.year, o.month, o.day).isoformat()
        return json.JSONEncoder.default(self, o)


class PropertyMapping(dict):
    """
    A dictionary where each key is guaranteed to be of type str and each value has a
    type corresponding to the key based on amcates "get_property_primitive_type" rules.
    """
    def __init__(self, E=None, **F):
        super().__init__()
        self.update(E, **F)

    def __setitem__(self, key: str, value: Union[str, int, float, datetime.datetime]):
        # Check for key type
        if not isinstance(key, str):
            raise ValueError("{} is not of type str, but is {} instead.".format(key, type(key)))

        if not is_valid_property_name(key):
            raise ValueError("This property name is not valid: {}".format(key))

        # None does not make sense in this context. The caller should use __delitem__ instead.
        if value is None:
            raise ValueError("Value can not be None. Delete it instead!")

        # Property types are determined by their name. As a result, we expect that type.
        expected_type = get_property_primitive_type(key)

        # Implicitly convert ints to floats (but not the other way around)
        if expected_type is float and isinstance(value, int):
            value = float(value)

        if not isinstance(value, expected_type):
            raise ValueError("Expected type {} for key {}. Got {} with type {} instead.".format(
                expected_type, key, value, type(value)
            ))

        super().__setitem__(key, value)

    def __repr__(self):
        return "<{}(props={})>".format(self.__class__.__name__, super(PropertyMapping, self).__repr__())

    def update(self, E=None, **F):
        """If update() fails, no guarantees are made about the resulting state of the mapping"""
        if E:
            for key, value in E.items():
                self[key] = value

        for key, value in F.items():
            self[key] = value

    @classmethod
    def fromdb(cls, d):
        new = PropertyMapping()
        for key, value in d.items():
            expected_type = get_property_primitive_type(key)
            if expected_type == datetime.datetime:
                new[key] = iso8601.parse_date(value)
            else:
                new[key] = expected_type(value)
        return new


class PropertyField(JSONField):
    """JSON field specifically made for Article.properties. It knows about the types stored
    and will convert between them automatically."""
    empty_strings_allowed = False
    description = 'A JSON object'
    default_error_messages = {
        'invalid': "Value must be a PropertyMapping.",
    }

    def get_prep_value(self, value):
        if value is not None:
            return Json(value, dumps=functools.partial(json.dumps, cls=DateTimeEncoder))
        return None

    def validate(self, value, model_instance):
        if value is None:
            return

        if not isinstance(value, PropertyMapping):
            raise ValueError("value must be a PropertyMapping")

    def get_default(self):
        return PropertyMapping()

    def to_python(self, value: PropertyMapping):
        if not isinstance(value, PropertyMapping):
            raise ValidationError("Always supply a PropertyMapping or dict when setting Article.properties.")

        return super(PropertyField, self).to_python(value)

    @classmethod
    def from_db_value(cls, value, expression, connection, context):
        return PropertyMapping.fromdb(value)


class Article(AmcatModel):
    """
    Class representing a newspaper article
    """
    __label__ = 'title'

    id = models.AutoField(primary_key=True, db_column="article_id")
    project = models.ForeignKey("amcat.Project", db_index=True, related_name="articles")

    # dublin core metadata fields
    date = models.DateTimeField()
    title = models.TextField()
    url = models.TextField(null=True, blank=True, max_length=750)
    text = models.TextField()

    # hash and parent / tree structure
    hash = HashField(unique=True, max_length=64)
    parent_hash = HashField(null=True, blank=True, max_length=64)

    # flexible properties, should be flat str:primitive (json) dict 
    properties = PropertyField(null=False, blank=False)

    def __init__(self, *args, **kwargs):
        if kwargs:
            if args:
                raise ValueError("Specify either non-keyword args or keyword args.")
            static_fields = self.get_static_fields()
            properties = kwargs.pop("properties", {})
            properties.update({k: kwargs.pop(k) for k in set(kwargs) if k not in static_fields})
            kwargs['properties'] = properties
        super(Article, self).__init__(*args, **kwargs)

        self._highlighted = False

    def __setattr__(self, key, value):
        if not key.startswith("_") and key not in self.get_static_fields():
            raise ValueError("You are setting Article.{} = {}. This is probably not what you "
                             "want. Please use Article.set_property.".format(key, value))
        super(Article, self).__setattr__(key, value)

    class Meta():
        db_table = 'articles'
        app_label = 'amcat'

    def get_properties(self):
        return self.properties

    def get_property(self, name, default=EMPTY):
        """Get article property regardsless whether or not it is defined as a 'real' property
        or stored in Article.properties."""
        if name in self.get_static_fields():
            return getattr(self, name)

        properties = self.get_properties()
        if name not in properties:
            if default is EMPTY:
                raise KeyError("Field {} does not exist on article {}".format(name, self.id))
            return default
        return properties[name]

    def set_property(self, key: str, value: Any):
        """
        Set property on this article regardless of whether it is a 'real' property or a 'fake'
        one stored in Article.properties.
        """
        if key in self.get_static_fields():
            setattr(self, key, value)
        else:
            properties = self.get_properties()
            properties[key] = value

    @classmethod
    @functools.lru_cache()
    def get_static_fields(cls):
        return frozenset(f.name for f in cls._meta.fields) | frozenset(["project_id", "project"])

    @classmethod
    def fromdict(cls, properties: Dict[str, Any]):
        """Construct an Article object from a dictionary."""
        properties = properties.copy()
        article = cls(properties=properties)
        article_fields = {f.name for f in cls._meta.fields}
        for field_name, value in list(properties.items()):
            if field_name in ("hash", "id"):
                raise ValueError("You cannot set {}.{}".format(cls.__name__, field_name))
            elif field_name in article_fields:
                setattr(article, field_name, value)
                properties.pop(field_name)
        article.compute_hash()
        return article

    def highlight(self, query, escape=True, keep_em=True):
        """
        Highlight title and text property by inserting HTML tags (em). You won't be able to
        call save() after calling this method.

        @param query: elastic query used for highlighting
        @type query: str

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
        self.title = highlighted.get("title", self.title)

        if escape:
            self.text = escape_filter(self.text)
            self.title = escape_filter(self.title)

            if keep_em:
                self.text = unescape_em(self.text)
                self.title = unescape_em(self.title)

        return highlighted

    @property
    def children(self):
        """Return a sequence of all child articles (eg reactions to a post)"""
        return Article.objects.filter(parent_hash = self.hash)

    @property
    def parent(self):
        if self.parent_hash:
            try:
                return Article.objects.get(hash=self.parent_hash)
            except Article.DoesNotExist:
                pass

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
        return "<Article %s: %r>" % (self.id, self.title)

    def get_article_dict(self, **kargs):
        return amcates.get_article_dict(self, **kargs)

    def compute_hash(self):
        hash = self.get_article_dict()['hash']
        if self.hash and self.hash != hash:
            raise ValueError("Incorrect hash specified")
        self.hash = hash
        return hash

    @classmethod
    def exists(cls, article_ids, batch_size=500):
        """
        Filters the given articleids to remove non-existing ids
        """
        for batch in splitlist(article_ids, itemsperbatch=batch_size):
            for aid in Article.objects.filter(pk__in=batch).values_list("pk", flat=True):
                yield aid

    @classmethod
    def create_articles(cls, articles, articleset=None, articlesets=None, deduplicate=True, monitor=NullMonitor()):
        """
        Add the given articles to the database, the index, and the given set

        Duplicates are detected and have ._duplicate and .id set (and are added to sets)

        @param articles: a collection of objects with the necessary properties (.title etc)
        @param articleset(s): articleset object(s), specify either or none
        """
        monitor = monitor.submonitor(total=4)

        if articlesets is None:
            articlesets = [articleset] if articleset else []

        # Check for ids
        for a in articles:
            if a.id is not None:
                raise ValueError("Specifying explicit article ID in save not allowed")

        # Compute hashes, mark all articles as non-duplicates
        for a in articles:
            a.compute_hash()
            a._duplicate = None

        # Determine which articles are dupes of each other, *then* query the database
        # to check if the database has any articles we just got.
        if deduplicate:
            hashes = collections.defaultdict(list)  # type: Dict[bytes, List[Article]]

            for a in articles:
                if a.hash in hashes:
                    a._duplicate = hashes[a.hash][0]
                else:
                    hashes[a.hash].append(a)

            # Check database for duplicates
            if hashes:
                monitor.update(message="Checking _duplicates based on hash..")
                results = Article.objects.filter(hash__in=hashes.keys()).only("hash")
                for orig in results:
                    dupes = hashes[orig.hash]
                    for dupe in dupes:
                        dupe._duplicate = orig
                        dupe.id = orig.id
        else:
            monitor.update()

        # Save all non-duplicates
        to_insert = [a for a in articles if not a._duplicate]
        monitor.update(message="Inserting {} articles into database..".format(len(to_insert)))
        if to_insert:
            result = bulk_insert_returning_ids(to_insert)
            for a, inserted in zip(to_insert, result):
                a.id = inserted.id
            dicts = [a.get_article_dict(sets=[aset.id for aset in articlesets]) for a in to_insert]
            amcates.ES().bulk_insert(dicts, batch_size=100, monitor=monitor)
        else:
            monitor.update()

        # At this point we can still have internal duplicates. Give them an ID as well.
        for article in articles:
            if article.id is None and article._duplicate is not None:
                article.id = article._duplicate.id

        if not articlesets:
            monitor.update(2)
            return articles

        # add new articles and _duplicates to articlesets
        monitor.update(message="Adding articles to articleset..")
        new_ids = {a.id for a in to_insert}
        dupes = {a._duplicate.id for a in articles if a._duplicate} - new_ids
        for aset in articlesets:
            if new_ids:
                aset.add_articles(new_ids, add_to_index=False, monitor=monitor)
            else:
                monitor.update()

            if dupes:
                aset.add_articles(dupes, add_to_index=True, monitor=monitor)
            else:
                monitor.update()

        return articles


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
            role = Project.objects.get(pk=pid).get_role_id(user)
            project_cache[pid] = role and (role >= ROLE_PROJECT_READER)
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
