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

class PolicyTestCase tests whether code is "AmCAT compliant"
Intended usage is as part of normal django unit testing: make sure that
the test class subclasses PolicyTestCase, and run testing as normal.

functions create_test_* create test objects for use in unit tests
"""

from __future__ import unicode_literals, print_function, absolute_import
import os.path, os, inspect
from contextlib import contextmanager
from django.test import TestCase
from unittest import TestLoader


LICENSE = """###########################################################################
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

from . import toolkit

# use unique ids for different model objects to avoid false negatives
ID = 99999
def _get_next_id():
    global ID
    ID += 1
    return ID

def create_test_user(**kargs):
    """Create a user to be used in unit testing"""
    from amcat.models.user import Affiliation, User#, Language
    if 'affiliation' not in kargs:
        kargs['affiliation'] = Affiliation.objects.create()
    if 'username' not in kargs:
        kargs['username'] = "testuser_%i" % User.objects.count()
    if 'email' not in kargs:
        kargs['email'] = "testuser_%i@example.com" % User.objects.count()
    if 'fullname' not in kargs:
        kargs['fullname'] = kargs['username']
    # if 'language' not in kargs:
        # kargs['language'] = Language.objects.all()[0]
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return User.objects.create(**kargs)
    #return User.create_user(**kargs)

def create_test_project(**kargs):
    """Create a project to be used in unit testing"""
    from amcat.models.project import Project
    u = create_test_user()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return Project.objects.create(owner=u, insert_user=u, **kargs)
    
def create_test_schema(**kargs):
    """Create a test schema to be used in unit testing"""
    from amcat.models.coding.codingschema import CodingSchema
    p = create_test_project()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return CodingSchema.objects.create(project=p, **kargs)

def create_test_medium(**kargs):
    from amcat.models.medium import Medium
    from amcat.models.language import Language
    if "language" not in kargs: kargs["language"] = Language.objects.get(pk=1)
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return Medium.objects.create(**kargs)
    
def create_test_article(**kargs):
    """Create a test article"""
    from amcat.models.article import Article
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "date" not in kargs: kargs["date"] = "2000-01-01"
    if "medium" not in kargs: kargs["medium"] = create_test_medium()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return Article.objects.create(**kargs)

def create_test_sentence(**kargs):
    """Create a test sentence"""    
    from amcat.models.sentence import Sentence
    if "article" not in kargs: kargs["article"] = create_test_article()
    if "sentence" not in kargs: 
        kargs["sentence"] = "Test sentence number %i." % len(Sentence.objects.all())
    if "parnr" not in kargs: kargs["parnr"] = 1
    if "sentnr" not in kargs: kargs["sentnr"] = 1
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return Sentence.objects.create(**kargs)


def create_test_set(articles=0, **kargs):
    """Create a test (Article) set"""
    from amcat.models.articleset import ArticleSet
    if "name" not in kargs: kargs["name"] = "testset_%i" % len(ArticleSet.objects.all())
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    s = ArticleSet.objects.create(**kargs)
    if articles:
        for _x in range(int(articles)):
            s.add(create_test_article())
    return s
            

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
    from amcat.models.coding.coding import Coding

    if "codingjob" not in kargs:
        kargs["codingjob"] = create_test_job()
        
    if "article" not in kargs: kargs["article"] = kargs["codingjob"].articleset.articles.all()[0]
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return Coding.objects.create(**kargs)

def create_test_code(label=None, language=None, **kargs):
    """Create a test code with a label"""
    from amcat.models.coding.code import Code
    from amcat.models.language import Language
    if language is None: language = Language.objects.get(pk=1)
    if label is None: label = "testcode_%i" % len(Code.objects.all())
    if "id" not in kargs: kargs["id"] = _get_next_id()
    o = Code.objects.create(**kargs)
    o.add_label(language, label)
    return o

def create_test_codebook(**kargs):
    """Create a test codebook"""
    from amcat.models.coding.codebook import Codebook, get_codebook
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "name" not in kargs: kargs["name"] = "testcodebook_%i" % Codebook.objects.count()
    if "id" not in kargs: kargs["id"] = _get_next_id()
    c = Codebook.objects.create(**kargs)
    return get_codebook(c.id)

def create_test_word(lemma=None, word=None, language=None, pos="N"):
    """Create a test word"""
    from amcat.models.word import Word, Lemma
    from amcat.models.language import Language
    if language is None: language = Language.objects.get(pk=1)
    if not lemma: lemma = "testlemma_%i" % Lemma.objects.count()
    if not word: word = "testword_%i" % Word.objects.count()
    l = Lemma.objects.create(pos=pos, lemma=lemma, language=language)
    return Word.objects.create(id=_get_next_id(), lemma=l, word=word)

def create_test_analysis(**kargs):
    from amcat.models.analysis import Analysis
    from amcat.models.language import Language
    if 'language' not in kargs: kargs['language'] = Language.objects.get(pk=1)
    if "id" not in kargs: kargs["id"] = _get_next_id()
    return Analysis.objects.create(**kargs)

class PolicyTestCase(TestCase):
    """
    TestCase subclass that can be used to easily check whether a module is
    'AmCAT compliant'. Checks for license banner and pylint.
    Define PYLINT_IGNORE_EXTRA (should be a sequence) to ignore specific messages
    for the target module. Override PYLINT_IGNORE for more control.
    If the target module is not the module that the test case is defined in,
    define the TARGET_MODULE class member (point to the imported module, not a string)
    This will make sure that both the defining module and the TARGET_MODULE are compliant
    """
    
    PYLINT_IGNORE = ("C0321", "C0103", "C0302",
                     "W0232", "W0404", "W0511", "W0142", "W0141", "W0106",
                     "R0903", "R0904", "R0913", "R0201", 'R0902',
                     "E1101", # 'X has no member Y' easily mislead by django magic members
                     "E1103", # pylint sucks at inheritance
                     )
    PYLINT_IGNORE_EXTRA = () 
    TARGET_MODULE = None

    def setUp(self):
        # codebooks have a global id:object cache, which is messed up by clearing the database
        # between test cases. So, reset it before every test to be sure.
        from amcat.models.coding.codebook import clear_codebook_cache
        clear_codebook_cache()

        # Make sure that current_user() exists
        try:
            from amcat.models.user import current_user, current_username, User
            current_user()
        except User.DoesNotExist:
            create_test_user(username = current_username())
        
        super(PolicyTestCase, self).setUp()
    
    def _getmodule(self):
        """
        Get the target module for testing. If TARGET_MODULE is specified, use that,
        otherwise, use the module defining the class
        """
        return getattr(self, "TARGET_MODULE", inspect.getmodule(self))
    
    def test_policy_license(self, mod=None):
        """Does the module have a license banner?"""
        if mod is None: mod = inspect.getmodule(self)
        comments = inspect.getcomments(mod)
        if comments is None: comments = ''
        self.assertIn(LICENSE, comments,
                      "License string not found in module {0}".format(mod.__name__))

    def test_policy_license_target(self):
        """Does the TARGET_MODULE (if applicable) have a license banner?"""
        if self.TARGET_MODULE:
            self.test_policy_license(mod=self.TARGET_MODULE)

    def test_policy_lint(self, mod=None):
        """
        Test whether the module the test is declared in passes pylint validation
        Use the PYLINT environment variable to control execution: FULL, ERRORS, or NONE
        (case-insensitive, first letter is sufficient, ie PYLINT=n)
        """
        if mod is None: mod = inspect.getmodule(self)
        pylint_option = os.environ.get("PYLINT", "FULL").lower()
        if pylint_option.startswith("n"): return
        fn = inspect.getsourcefile(mod)
        errorsonly = pylint_option.startswith("e")
        call = ["pylint"]
        if errorsonly: call += ["--errors-only"]
        # Which messages to ignore?
        ignore = set(self.PYLINT_IGNORE)
        if self.PYLINT_IGNORE_EXTRA: ignore |= set(self.PYLINT_IGNORE_EXTRA)
        if ignore: call += ["-d%s" % ",".join(ignore)] 
        call += [r'--no-docstring-rgx="(__.*__|^Meta$|^Test)"'] # ignore docstrings
        call += ["--include-ids=y","--reports=n"] # give message ids, no reports
        call += ["--max-line-length=100"]
        call += ["--good-names=i,j,k,log"]
        call += [fn]

        out, err = toolkit.execute(" ".join(call))
        err = err.replace("No config file found, using default configuration", "").strip()
        if err: raise Exception(err)
        self.assertEqual(out.strip(), '', "PyLint errors:\n%s" % out)

        

    def test_policy_pylint_target(self):
        """Does the TARGET_MODULE (if applicable) pass pylint checking?"""
        if self.TARGET_MODULE:
            self.test_policy_lint(mod=self.TARGET_MODULE)

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
    

            
class TestAmcatTest(PolicyTestCase):
    PYLINT_IGNORE_EXTRA = "E1103",

    def test_createtestuser_unique(self):
        """Does create_test_user return a unique user?"""
        u = create_test_user()
        u2 = create_test_user()
        self.assertNotEqual(u, u2)

    def test_createtestproject_unique(self):
        """Does create_test_user return a unique user?"""
        p = create_test_project()
        p2 = create_test_project()
        self.assertNotEqual(p, p2)
        
        
        




class TestDiscoverer(TestLoader):
    def __init__(self, *args, **kargs):
        super(TestDiscoverer, self).__init__(*args, **kargs)
        self.test_classes = set()
    def suiteClass(self, tests):
        for test in tests:
            if test:
                self.test_classes.add(test.__class__)

def get_test_classes(module="amcat"):
    d = TestDiscoverer()
    d.discover(module, pattern="*.py")
    return d.test_classes
