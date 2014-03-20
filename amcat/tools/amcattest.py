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

from __future__ import unicode_literals, print_function, absolute_import
import os
from contextlib import contextmanager
from functools import wraps

try:
    from django.test import TestCase
except ImportError:
    from unittest import TestCase
import unittest
import logging; log = logging.getLogger(__name__)

from django.conf import settings

# use unique ids for different model objects to avoid false negatives
ID = 1000000000
def _get_next_id():
    global ID
    ID += 1
    return ID

def skip_slow_tests():
    """Should we skip the slow tests, e.g. Solr, Alpino etc"""
    return os.environ.get('DJANGO_SKIP_SLOW_TESTS') in ("1","Y", "ON")

def create_test_user(**kargs):
    """Create a user to be used in unit testing"""
    from amcat.models.user import Affiliation, User, create_user
    if 'affiliation' not in kargs:
        kargs['affiliation'] = Affiliation.objects.create()
    if 'username' not in kargs:
        kargs['username'] = "testuser_%i" % User.objects.count()
    if 'email' not in kargs:
        kargs['email'] = "testuser_%i@example.com" % User.objects.count()
    if 'first_name' not in kargs:
        kargs['first_name'] = kargs['username']
    if 'last_name' not in kargs:
        kargs['last_name'] = kargs['username']
    if 'language' not in kargs:
        kargs['language'] = get_test_language()
    if 'role' not in kargs:
        kargs['role'] = get_test_role()
    if 'password' not in kargs:
        kargs['password'] =  'test'
    #if "id" not in kargs: kargs["id"] = _get_next_id()
    return create_user(**kargs)
    #return User.create_user(**kargs)

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
    """Set up a simple coding schema with fields to use for testing
    Returns codebook, schema, textfield, numberfield, codefield
    """
    from amcat.models import CodingSchemaFieldType, CodingSchemaField

    if codebook is None:
        codebook = create_test_codebook()
    schema = create_test_schema(**kargs)

    fields = []
    for i, (label, type_id) in enumerate([
            ("text", 1),
            ("number", 2),
            ("code", 5)]):
        cb = codebook if label == "code" else None
        fieldtype = CodingSchemaFieldType.objects.get(pk=type_id)
        f = CodingSchemaField.objects.create(codingschema=schema, fieldnr=i, label=label,
                                             fieldtype=fieldtype, codebook=cb)
        fields.append(f)

    return (schema, codebook) + tuple(fields)

def get_test_language(**kargs):
    from amcat.models.language import Language
    from amcat.tools import djangotoolkit
    return djangotoolkit.get_or_create(Language, label='en')

def get_test_role(**kargs):
    from amcat.models import Role
    from amcat.tools import djangotoolkit
    return djangotoolkit.get_or_create(Role, label='admin', projectlevel=False)

def create_test_medium(**kargs):
    from amcat.models.medium import Medium
    if "language" not in kargs: kargs["language"] = get_test_language()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    if "name" not in kargs: kargs["name"] = "Medium_%i" % kargs["id"]
    return Medium.objects.create(**kargs)

def create_test_article(create=True, articleset=None, check_duplicate=False, **kargs):
    """Create a test article"""
    from amcat.models.article import Article
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "date" not in kargs: kargs["date"] = "2000-01-01"
    if "medium" not in kargs: kargs["medium"] = create_test_medium()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    if 'headline' not in kargs: kargs['headline'] = 'test headline'

    a = Article(**kargs)
    if create:
        Article.create_articles([a], articleset, check_duplicate=check_duplicate)
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

def create_test_set(articles=0, **kargs):
    """Create a test (Article) set"""
    from amcat.models.articleset import ArticleSet, Article
    if "name" not in kargs: kargs["name"] = "testset_%i" % len(ArticleSet.objects.all())
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    s = ArticleSet.objects.create(**kargs)
    if type(articles) == int:
        articles = [create_test_article(create=False) for _x in range(articles)]
        Article.create_articles(articles, articleset=s, check_duplicate=False)
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
    if "articleschema" not in kargs: kargs["articleschema"] = create_test_schema()
    if "coder" not in kargs: kargs["coder"] = create_test_user()
    if "articleset" not in kargs: kargs["articleset"] = create_test_set(articles=narticles)
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return CodingJob.objects.create(**kargs)

def create_test_coding(**kargs):
    """Create a test coding object"""
    from amcat.models.coding.coding import create_coding

    if "codingjob" not in kargs:
        kargs["codingjob"] = create_test_job()

    if "article" not in kargs: kargs["article"] = kargs["codingjob"].articleset.articles.all()[0]
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return create_coding(**kargs)

def create_test_code(label=None, language=None, codebook=None, parent=None, **kargs):
    """Create a test code with a label"""
    from amcat.models.coding.code import Code
    from amcat.models.language import Language
    if language is None: language = Language.objects.get(pk=1)
    if label is None: label = "testcode_%i" % len(Code.objects.all())
    if "id" not in kargs: kargs["id"] = _get_next_id()
    o = Code.objects.create(**kargs)
    o.add_label(language, label)
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
    parents = {"A1a":"A1", "A1b":"A1", "A1":"A", "A2":"A", "B1":"B", "A":None, "B":None}
    codes = {l : create_test_code(label=l) for l in parents}
    codebook = create_test_codebook()
    for code, parent in parents.items():
        codebook.add_code(codes[code], codes.get(parent))
    return codebook, codes

def create_test_plugin(**kargs):
    from amcat.models import Plugin, PluginType
    if "id" not in kargs: kargs["id"] = _get_next_id()
    if "class_name" not in kargs: kargs["class_name"] = "amcat.tools.amcattest.AmCATTestCase"
    if "plugin_type" not in kargs: kargs["plugin_type"] = PluginType.objects.get(pk=1)
    return Plugin.objects.create(**kargs)

class AmCATTestCase(TestCase):
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

    @classmethod
    def tearDownClass(cls):
        if settings.ES_INDEX.endswith("__unittest"):
            settings.ES_INDEX = settings.ES_INDEX[:len("__unittest")]

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

def use_elastic(func):
    """
    Decorate a test function to make sure that:
    - The ElasticSearch server can be reached (skips otherwise)
    - The '__unittest' index exists and is empty
    """
    @wraps(func)
    def inner(*args, **kargs):
        from amcat.tools.amcates import ES
        if not settings.ES_INDEX.endswith("__unittest"):
            settings.ES_INDEX += "__unittest"
        es = ES()
        if not es.es.ping():
            raise unittest.SkipTest("ES not enabled")
        es.delete_index()
        ES().check_index()
        return func(*args, **kargs)
    return inner

def get_tests_from_suite(suite):
    for e in suite:
        if isinstance(e, unittest.TestSuite):
            for test in get_tests_from_suite(e):
                yield test
        elif str(type(e)) == "<class 'unittest.loader.ModuleImportFailure'>":
            try:
                getattr(e, e._testMethodName)()
            except:
                log.exception("Exception on importing test class")
        elif isinstance(e, unittest.TestCase):
            yield e
        else:
            raise ValueError("Cannot parse type {e!r}".format(**locals()))

def get_test_classes(module="amcat"):
    tests = unittest.defaultTestLoader.discover(start_dir=module, pattern="*.py")
    for test in get_tests_from_suite(tests):
        yield test.__class__
