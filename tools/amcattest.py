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
import unittest, os.path, os, inspect


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
    
def create_test_user():
    """Create a user to be used in unit testing"""
    from amcat.model.user import Affiliation, User
    aff = Affiliation.objects.all()[0]
    username = "testuser_%i" % len(User.objects.all())
    return User.objects.create(affiliation=aff, username=username, email=username)

def create_test_project(**kargs):
    """Create a project to be used in unit testing"""
    from amcat.model.project import Project
    u = create_test_user()
    return Project.objects.create(owner=u, insert_user=u, **kargs)
    
def create_test_schema(**kargs):
    """Create a test schema to be used in unit testing"""
    from amcat.model.coding.annotationschema import AnnotationSchema
    p = create_test_project()
    return AnnotationSchema.objects.create(project=p, **kargs)

def create_test_article(**kargs):
    """Create a test article"""
    from amcat.model.article import Article
    from amcat.model.medium import Medium
    from amcat.model.language import Language
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "date" not in kargs: kargs["date"] = "2000-01-01"
    l = Language.objects.get(pk=1)
    m = Medium.objects.create(language=l)
    return Article.objects.create(medium=m, **kargs)

def create_test_sentence(**kargs):
    """Create a test sentence"""    
    from amcat.model.sentence import Sentence
    if "article" not in kargs: kargs["article"] = create_test_article()
    if "sentence" not in kargs: 
        kargs["sentence"] = "Test sentence number %i." % len(Sentence.objects.all())
    if "parnr" not in kargs: kargs["parnr"] = 1
    if "sentnr" not in kargs: kargs["sentnr"] = 1
    return Sentence.objects.create(**kargs)


def create_test_set(articles=0, **kargs):
    """Create a test (Article) set"""
    from amcat.model.set import Set
    if "name" not in kargs: kargs["name"] = "testset_%i" % len(Set.objects.all())
    if "project" not in kargs: kargs["project"] = create_test_project()
    s = Set.objects.create(**kargs)
    if articles:
        for _x in range(int(articles)):
            s.articles.add(create_test_article())
    return s
            

def create_test_job(**kargs):
    """Create a test Coding Job"""
    from amcat.model.coding.codingjob import CodingJob
    if "insertuser" not in kargs: kargs["insertuser"] = create_test_user()
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "unitschema" not in kargs: kargs["unitschema"] = create_test_schema()
    if "articleschema" not in kargs: kargs["articleschema"] = create_test_schema()
    return CodingJob.objects.create(**kargs)

def create_test_annotation(job=None, **kargs):
    """Create a test annotation object"""
    from amcat.model.coding.codingjob import CodingJobSet
    from amcat.model.coding.annotation import Annotation

    if "codingjobset" not in kargs:
        if job is None: job = create_test_job()
        s = create_test_set(articles=2)
        kargs["codingjobset"] = CodingJobSet.objects.create(codingjob=job, articleset=s, 
                                                            coder=job.insertuser)
    if "article" not in kargs: kargs["article"] = kargs["codingjobset"].articleset.articles.all()[0]
    return Annotation.objects.create(**kargs)

def create_test_code(label=None, language=None, **kargs):
    """Create a test code with a label"""
    from amcat.model.coding.code import Code
    from amcat.model.language import Language
    if language is None: language = Language.objects.get(pk=1)
    if label is None: label = "testcode_%i" % len(Code.objects.all())
    o = Code.objects.create(**kargs)
    o.add_label(language, label)
    return o

def create_test_codebook(**kargs):
    """Create a test codebook"""
    from amcat.model.coding.codebook import Codebook
    if "project" not in kargs: kargs["project"] = create_test_project()
    if "name" not in kargs: kargs["name"] = "testcodebook_%i" % Codebook.objects.count()
    return Codebook.objects.create(**kargs)


class PolicyTestCase(unittest.TestCase):
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
                     "W0232", "W0404", "W0511", "W0142",
                     "R0903", "R0904", "R0913", "R0201", 'R0902',
                     "E1101", # 'X has no member Y' easily mislead by django magic members
                     "E1103", # pylint sucks at inheritance
                     )
    PYLINT_IGNORE_EXTRA = () 
    TARGET_MODULE = None

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
            self.test_policy_pylint(mod=self.TARGET_MODULE)

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
        
        
        
        
