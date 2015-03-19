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

from amcat.tools import amcattest
from amcat.tools import classtools


class _TestClass(object):
    pass


class TestClassTools(amcattest.AmCATTestCase):
    def test_get_caller(self):
        fn, line, func = classtools.get_caller(depth=0)
        self.assertEqual(fn, __file__.replace(".pyc", ".py"))
        self.assertEqual(func, "test_get_caller")

        def _test():
            return classtools.get_caller()

        fn, line, func = _test()
        self.assertEqual(fn, __file__.replace(".pyc", ".py"))
        self.assertEqual(func, "test_get_caller")

    def test_get_calling_module(self):
        self.assertEqual(classtools.get_calling_module(depth=0), self.__module__)

    def test_get_class_from_module(self):
        m = TestClassTools.__module__
        cls = classtools.get_class_from_module(m, amcattest.AmCATTestCase)
        self.assertEqual(cls, self.__class__)
        cls = classtools.get_class_from_module(m, TestClassTools)
        self.assertEqual(cls, TestClassTools)
        import unittest

        cls = classtools.get_class_from_module(m, unittest.TestCase)
        self.assertEqual(cls, TestClassTools)

        from amcat.models.article import Article

        self.assertRaises(ValueError, classtools.get_class_from_module, m, Article.__class__)

    def test_import_attribute(self):
        t = classtools.import_attribute("amcat.tools.tests.test_classtools", "TestClassTools")
        self.assertEqual(t.__name__, 'TestClassTools')
        t = classtools.import_attribute("amcat.tools.tests.test_classtools.TestClassTools")
        self.assertRaises(ImportError, classtools.import_attribute, "__wva_does_not_exist")
        self.assertRaises(ImportError, classtools.import_attribute,
                          "amcat.tools.classtools", "__wva_does_not_exist")
        self.assertRaises(ImportError, classtools.import_attribute,
                          "amcat.tools.classtools.__wva_does_not_exist")

        self.assertEqual(classtools.import_attribute(u"amcat.models.article").__name__, "amcat.models.article")

    def test_get_classes_from_package(self):
        package = self.__module__
        self.assertEqual(set(classtools.get_classes_from_package(package)), {_TestClass, TestClassTools})
        from unittest import TestCase

        self.assertEqual(set(classtools.get_classes_from_package(package, superclass=TestCase)),
                         {TestClassTools})
        self.assertEqual(set(classtools.get_classes_from_package(package, superclass=dict)), set())
