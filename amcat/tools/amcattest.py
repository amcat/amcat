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
Module to assist testing in AmCAT.

class AmCATTestCase tests whether code is "AmCAT compliant"
Intended usage is as part of normal django unit testing: make sure that
the test class subclasses AmCATTestCase, and run testing as normal.

functions create_test_* create test objects for use in unit tests
"""


import datetime
import logging
import os
import unittest
from collections import OrderedDict
from contextlib import contextmanager
from functools import wraps
from urllib.parse import urljoin
from uuid import uuid4

import dateparser
import shutil
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache
from django.test import TestCase
from iso8601 import iso8601
from splinter import Browser

from amcat.models import ArticleSet
from amcat.tools.amcates import ES, get_property_primitive_type

log = logging.getLogger(__name__)


# use unique ids for different model objects to avoid false negatives
ID = 1000000000
def _get_next_id():
    global ID
    ID += 1
    return ID


def skip_slow_tests():
    """Should we skip the slow tests, e.g. Solr, Alpino etc"""
    return os.environ.get('AMCAT_SKIP_SLOW_TESTS') in ("1","Y", "ON")


def create_test_query(**kargs):
    from amcat.models import Query
    if "name" not in kargs:
        kargs["name"] = "Test query"
    if "parameters" not in kargs:
        kargs["parameters"] = [1,2,3]

    if "project" not in kargs:
        kargs["project"] = create_test_project()
    if "user" not in kargs:
        kargs["user"] = create_test_user()
    return Query.objects.create(**kargs)


def create_test_user(**kargs):
    """Create a user to be used in unit testing"""
    from amcat.models.user import  User, create_user
    if 'username' not in kargs:
        kargs['username'] = "testuser_%i" % User.objects.count()
    if 'email' not in kargs:
        kargs['email'] = "testuser_%i@example.com" % User.objects.count()
    if 'first_name' not in kargs:
        kargs['first_name'] = kargs['username']
    if 'last_name' not in kargs:
        kargs['last_name'] = kargs['username']
    if 'password' not in kargs:
        kargs['password'] =  'test'
    return create_user(**kargs)


def create_test_project(**kargs):
    """Create a project to be used in unit testing"""
    from amcat.models.project import Project
    from amcat.models.authorisation import ProjectRole, ROLE_PROJECT_ADMIN
    if "owner" not in kargs: kargs["owner"] = create_test_user()
    if "insert_user" not in kargs: kargs["insert_user"] = kargs["owner"]
    if "id" not in kargs: kargs["id"] = _get_next_id()
    p = Project.objects.create(**kargs)
    ProjectRole.objects.create(project=p, user=p.owner, role_id=ROLE_PROJECT_ADMIN)
    return p


def create_test_schema(**kargs):
    """Create a test schema to be used in unit testing"""
    from amcat.models.coding.codingschema import CodingSchema
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    if 'name' not in kargs: kargs['name'] = "testschema_%i" % CodingSchema.objects.count()
    return CodingSchema.objects.create(**kargs)


def create_test_schema_with_fields(codebook=None, **kargs):
    """Set up a simple codingschema with fields to use for testing
    Returns codebook, schema, textfield, numberfield, codefield
    """
    from amcat.models import CodingSchemaFieldType, CodingSchemaField

    if codebook is None:
        codebook, _ = create_test_codebook_with_codes()
    schema = create_test_schema(**kargs)

    fields = []
    for i, (label, type_id, cb) in enumerate([
            ("text", 1, None),
            ("number", 2, None),
            ("code", 5, codebook),
            ("boolean", 7, None),
            ("quality", 9, None)]):
        fieldtype = CodingSchemaFieldType.objects.get(pk=type_id)
        f = CodingSchemaField.objects.create(codingschema=schema, fieldnr=i, label=label,
                                             fieldtype=fieldtype, codebook=cb)
        fields.append(f)

    return (schema, codebook) + tuple(fields)


def get_test_language(**kargs):
    from amcat.models.language import Language
    from amcat.tools import djangotoolkit
    return djangotoolkit.get_or_create(Language, label='en')


def _parse_date(s: str):
    date = dateparser.parse(s, ['%Y-%m-%d', '%d-%m-%Y'], settings={"STRICT_PARSING": True})
    if date is None:
        return iso8601.parse_date(s)
    return date


def create_test_article(create=True, articleset=None, deduplicate=True, properties=None, project=None, **kargs):
    """Create a test article"""
    from amcat.models.article import Article

    # Get static properties
    title = kargs.pop("title", "test title {}: {}".format(_get_next_id(), uuid4()))
    date = kargs.pop("date", datetime.datetime.now())
    url = kargs.pop("url", "http://example.com")
    text = kargs.pop("text", "Lorum Ipsum: {}".format(_get_next_id()))
    if project is None:
        project = articleset.project if articleset is not None else create_test_project()
    parent_hash = kargs.pop("parent_hash", None)
    hash = kargs.pop("hash", None)

    # Caller is allowed to pas date as string
    if isinstance(date, str):
        date = _parse_date(date)

    a = Article(title=title, date=date, url=url, text=text, project=project, parent_hash=parent_hash, hash=hash)

    if properties:
        for propname, value in properties.items():
            if get_property_primitive_type(propname) == datetime.datetime and isinstance(value, str):
                properties[propname] = _parse_date(value)
        a.properties.update(properties)

    if create:
        Article.create_articles([a], articleset, deduplicate=deduplicate)

    return a


def create_test_sentence(**kargs):
    """Create a test sentence"""
    from amcat.models.sentence import Sentence
    if "article" not in kargs: kargs["article"] = create_test_article()
    if "sentence" not in kargs:
        kargs["sentence"] = "Test sentence %i." % _get_next_id()
    if "parnr" not in kargs: kargs["parnr"] = 1
    if "sentnr" not in kargs: kargs["sentnr"] = _get_next_id()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return Sentence.objects.create(**kargs)


def create_test_set(articles=0, **kargs) -> ArticleSet:
    """Create a test (Article) set"""
    from amcat.models.articleset import ArticleSet, Article
    if "name" not in kargs: kargs["name"] = "testset_%i" % len(ArticleSet.objects.all())
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    s = ArticleSet.objects.create(**kargs)
    if type(articles) == int:
        if articles > 0:
            arts = [create_test_article(create=False) for _x in range(articles)]
            Article.create_articles(arts, articleset=s)
    elif articles:
        s.add_articles(articles)
    return s

def create_test_coded_article():
    # coded_article gets created automatically when a new job is created
    codingjob = create_test_job()
    return list(codingjob.coded_articles.all())[0]


def create_test_job(narticles=1, **kargs):
    """Create a test Coding Job"""
    from amcat.models.coding.codingjob import CodingJob
    if "insertuser" not in kargs: kargs["insertuser"] = create_test_user()
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "unitschema" not in kargs: kargs["unitschema"] = create_test_schema()
    if "articleschema" not in kargs: kargs["articleschema"] = create_test_schema(isarticleschema=True)
    if "coder" not in kargs: kargs["coder"] = create_test_user()
    if "articleset" not in kargs: kargs["articleset"] = create_test_set(articles=narticles)
    if "id" not in kargs: kargs["id"] = _get_next_id()
    if "name" not in kargs: kargs["name"] = "Test job {id}".format(**kargs)
    return CodingJob.objects.create(**kargs)

def create_test_coding(**kargs):
    """Create a test coding object"""
    from amcat.models.coding.coding import create_coding

    if "codingjob" not in kargs:
        kargs["codingjob"] = create_test_job()

    if "article" not in kargs: kargs["article"] = kargs["codingjob"].articleset.articles.all()[0]
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return create_coding(**kargs)

def create_test_code(label=None, extra_label=None, extra_language=None, codebook=None, parent=None, **kargs):
    """Create a test code with a label"""
    from amcat.models.coding.code import Code
    from amcat.models.language import Language
    if label is None: label = "testcode_%i" % len(Code.objects.all())
    if "id" not in kargs: kargs["id"] = _get_next_id()
    o = Code.objects.create(label=label, **kargs)

    if extra_label is not None:
        if extra_language is None: extra_language = Language.objects.get(pk=1)
        o.add_label(extra_language, extra_label)
    if codebook is not None:
        codebook.add_code(o, parent=parent)
    return o

def create_test_codebook(**kargs):
    """Create a test codebook"""
    from amcat.models.coding.codebook import Codebook
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "name" not in kargs: kargs["name"] = "testcodebook_%i" % Codebook.objects.count()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return Codebook.objects.create(**kargs)

def  create_test_codebook_with_codes():
    """
    Create a test codebook with codes like this
    A
     A1
      A1a
      A1b
     A2
    B
     B1
    @return: A pair of the codebook and the {label : code} dict
    """
    parents = OrderedDict((
        ("A1a", "A1"),
        ("A1b", "A1"),
        ("A1", "A"),
        ("A2", "A"),
        ("B1", "B"),
        ("A", None),
        ("B", None)
    ))
    codes = {l: create_test_code(label=l) for l in parents}
    codebook = create_test_codebook()
    for code, parent in reversed(list(parents.items())):
        codebook.add_code(codes[code], codes.get(parent))
    return codebook, codes


class AmCATTestCase(TestCase):
    fixtures = ['_initial_data.json',]

    @classmethod
    def setUpClass(cls):
        ES().check_index()
        ES().refresh()
        cache.clear()
        super(AmCATTestCase, cls).setUpClass()

    def setUp(self):
        super().setUp()
        ES().check_index()
        ES().refresh()
        cache.clear()

    @contextmanager
    def checkMaxQueries(self, n=0, action="Query", **outputargs):
        """Check that the action took at most n queries (which should be collected in seq)"""
        # lazy import to prevent cycles
        from amcat.tools.djangotoolkit import list_queries
        with list_queries(**outputargs) as l:
            yield
        m = len(l)
        if m > n:
            msg = """{} should take at most {} queries, but used {}""".format(action, n, m)
            for i, q in enumerate(l):
                msg += "\n({}) {}".format(i+1, q["sql"])
            self.fail(msg)

class AmCATLiveServerTestCase(StaticLiveServerTestCase):
    fixtures = ['_initial_data.json',]

    def get_url(self, relative_url):
        return urljoin(self.live_server_url, relative_url)

    def logout(self):
        self.browser.visit(self.get_url("/accounts/logout/"))

    def login(self, username, password):
        self.logout()
        self.browser.visit(self.get_url("/accounts/login/"))
        self.browser.fill_form({"username": username, "password": password})
        self.browser.find_by_css("[type=submit]")[0].click()

    @classmethod
    def setUpClass(cls):
        super(AmCATLiveServerTestCase, cls).setUpClass()
        from django.core.cache import cache
        if not shutil.which("geckodriver"):  # try/except gives warning from selenium destructor
            raise unittest.SkipTest("geckodriver needs to be in PATH for LiveServerTestCase")
        cls.browser = Browser(driver_name=os.environ.get("AMCAT_WEBDRIVER", "firefox"))

    def setUp(self):
        self.browser.visit(self.live_server_url)
        super(AmCATLiveServerTestCase, self).setUp()

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super(AmCATLiveServerTestCase, cls).tearDownClass()


def require_postgres(func):
    def run_or_skip(self, *args, **kargs):
        from django.db import connection
        if connection.vendor != 'postgresql':
            raise unittest.SkipTest("Test function {func.__name__} requires postgres".format(**locals()))
        return func(self, *args, **kargs)
    return run_or_skip


def skip_TODO(reason):
    def inner(func):
        def skip(self, *args, **kargs):
            raise unittest.SkipTest("TODO: {}. Skipping test {}".format(reason, func.__name__))
        return skip
    return inner

def use_java(func):
    from subprocess import Popen
    try:
        has_java = Popen(["java", "-version"]).wait() == 0
    except FileNotFoundError:
        has_java = False

    @wraps(func)
    def inner(*args, **kwargs):
        if not has_java:
            raise unittest.SkipTest("Java executable not found")
        return func(*args, **kwargs)

    return inner


def use_elastic(func):
    """
    Decorate a test function to make sure that:
    - The ElasticSearch server can be reached (skips otherwise)
    """
    @wraps(func)
    def inner(*args, **kargs):
        from amcat.tools import amcates

        amcates._KNOWN_PROPERTIES = None

        es = amcates.ES()
        if not es.es.ping():
            raise unittest.SkipTest("ES not enabled")
        es.delete_index()
        es.refresh()
        es.check_index()
        es.refresh()

        return func(*args, **kargs)
    return inner


def clear_cache(func):
    @wraps(func)
    def inner(*args, **kargs):
        cache.clear()
        return func(*args, **kargs)
    return inner
