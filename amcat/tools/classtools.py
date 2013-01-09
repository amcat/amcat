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
Toolkit of methods to deal with python classes and modules
"""

import os.path, sys, types, inspect

def import_attribute(module, attribute=None):
    """
    Import and return the attribute from the module
    If attribute is None, assume module is of form mo.du.le.attribute
    """
    if attribute is None:
        if "." in module:
            module, attribute = module.rsplit(".", 1)
        else:
            return __import__(module)
    mod = __import__(module, fromlist=[str(attribute)])
    try:
        return getattr(mod, attribute)
    except AttributeError:
        raise ImportError("Module %r has no attribute %r" % (module, attribute))

def guess_module(filename):
    """
    'Guess' te module name represented by the filename by getting its shortest route
    to the system path, *skipping the first member* if it is the current working directory
    """
    filename = os.path.abspath(filename)

    path = sys.path
    if path[0] == os.getcwd(): del path[0]
    path = set(path)
    dirname, filename = os.path.split(filename)
    module = [os.path.splitext(filename)[0]]
    while True:
        tail, head = os.path.split(dirname)
        module.insert(0, head)
        if dirname in path:
            return ".".join(module)
        if tail == dirname: raise ValueError("Cannot find module for %s" % filename)
        dirname = tail


def get_classes_from_module(module, superclass=None):
    """
    Get all classes in the given module.
    @param superclass: If given, only return subclasses of that class
    """
    m = import_attribute(module)
    for name in dir(m):
        obj = getattr(m, name)
        if not isinstance(obj, (type, types.ClassType)): continue
        if superclass is not None and not issubclass(obj, superclass): continue
        if obj.__module__ == module:
            yield obj


def get_classes_from_package(package, superclass=None):
    """
    Get all classes in the given package, recursively getting classes
    from the subpackages and modules contained in the package.
    @param superclass: If given, only return subclasses of that class
    """
    # yield classes directly in the package module
    for c in get_classes_from_module(package, superclass):
        yield c
    p = import_attribute(package)
    if not "__init__.py" in p.__file__: return # not a package -> done
    dirname = os.path.dirname(p.__file__)
    for item in os.listdir(dirname):
        fn = os.path.join(dirname, item)
        if os.path.isdir(fn):
            if os.path.exists(os.path.join(fn, "__init__.py")):
                for c in get_classes_from_package(package + "." + item, superclass):
                    yield c
        if item.endswith(".py") and item != "__init__.py" and '#' not in item:
            for c in get_classes_from_package(package + "." + item[:-3], superclass):
                yield c


def get_class_from_module(module, superclass=None):
    """
    Get the first class from the given module, or raise a ValueError if none found
    @param superclass: If given, limit to subclasses of that class
    """
    for obj in get_classes_from_module(module, superclass):
        return obj
    raise ValueError("Cannot find a %s subclass in %r" % (superclass.__name__, module))

def get_caller(depth=1):
    """Return the filename, lineno, function of the caller

    @param depth: A depth of 1 return the caller of the function calling this function;
                  depth 2 would be its caller etc.
    """
    depth = depth + 1 # me, caller, caller's caller
    return inspect.stack()[depth][1:4]

def get_calling_module(depth=1):
    """Return the module name of the caller

    @param depth: A depth of 1 return caller of the function calling this function;
                  depth two would mean that function's caller etc.
    """
    depth = depth + 1 # me, caller, caller's caller
    caller = inspect.stack()[depth][0] # mod, file, line, function
    return caller.f_globals['__name__']


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class _TestClass(object):
    pass

class TestClassTools(amcattest.PolicyTestCase):

    def test_get_caller(self):
        fn, line, func = get_caller(depth=0)
        self.assertEqual(fn, __file__.replace(".pyc",".py"))
        self.assertEqual(func, "test_get_caller")
        def _test():
            return get_caller()
        fn, line, func = _test()
        self.assertEqual(fn, __file__.replace(".pyc",".py"))
        self.assertEqual(func, "test_get_caller")

    def test_get_calling_module(self):
        self.assertEqual(get_calling_module(depth=0), self.__module__)

    def test_get_class_from_module(self):
        m = TestClassTools.__module__
        cls = get_class_from_module(m, amcattest.PolicyTestCase)
        self.assertEqual(cls, self.__class__)
        cls = get_class_from_module(m, TestClassTools)
        self.assertEqual(cls, TestClassTools)
        import unittest
        cls = get_class_from_module(m, unittest.TestCase)
        self.assertEqual(cls, TestClassTools)

        from amcat.models.article import Article
        self.assertRaises(ValueError, get_class_from_module, m, Article.__class__)

    def test_guess_module(self):
        # test this module and a random other module
        f = __file__
        self.assertEqual(guess_module(f), "amcat.tools.classtools")
        f = os.path.dirname(f)
        self.assertEqual(guess_module(f), "amcat.tools")
        from amcat.models import article
        f = article.__file__
        self.assertEqual(guess_module(f), "amcat.models.article")
        f = os.path.dirname(f)
        self.assertEqual(guess_module(f), "amcat.models")
        self.assertRaises(ValueError, guess_module,
                          "/__wva_does_not_exist/amcat/tools/toolkit.py")

    def test_import_attribute(self):
        t = import_attribute("amcat.tools.classtools", "TestClassTools")
        self.assertEqual(t.__name__, 'TestClassTools')
        t = import_attribute("amcat.tools.classtools.TestClassTools")
        self.assertRaises(ImportError, import_attribute, "__wva_does_not_exist")
        self.assertRaises(ImportError, import_attribute,
                          "amcat.tools.classtools", "__wva_does_not_exist")
        self.assertRaises(ImportError, import_attribute,
                          "amcat.tools.classtools.__wva_does_not_exist")

        self.assertEqual(import_attribute(u"amcat.nlp.frog").__name__, "amcat.nlp.frog")

    def test_get_classes_from_package(self):
        package = self.__module__
        self.assertEqual(set(get_classes_from_package(package)), set([_TestClass, TestClassTools]))
        from unittest import TestCase
        self.assertEqual(set(get_classes_from_package(package, superclass=TestCase)),
                         set([TestClassTools]))
        self.assertEqual(set(get_classes_from_package(package, superclass=dict)), set())
