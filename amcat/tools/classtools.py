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

import os.path
import types
import inspect


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


def get_qualified_name(cls):
    return ".".join([cls.__module__, cls.__name__])


def get_classes_from_module(module, superclass=None):
    """
    Get all classes in the given module.
    @param superclass: If given, only return subclasses of that class
    """
    m = import_attribute(module)
    for name in dir(m):
        obj = getattr(m, name)
        if not isinstance(obj, (type, type)): continue
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
    if not "__init__.py" in p.__file__: return  # not a package -> done
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
    depth += 1  # me, caller, caller's caller
    return inspect.stack()[depth][1:4]


def get_calling_module(depth=1):
    """Return the module name of the caller

    @param depth: A depth of 1 return caller of the function calling this function;
                  depth two would mean that function's caller etc.
    """
    depth += 1  # me, caller, caller's caller
    caller = inspect.stack()[depth][0]  # mod, file, line, function
    return caller.f_globals['__name__']


