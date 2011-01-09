from __future__ import unicode_literals, print_function, absolute_import
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

import logging; log = logging.getLogger(__name__)

class LB(object):
    def __init__(self, classname, modulename=None, package="amcat.model", sub=None):
        self.classname = classname
        if modulename is None: modulename = classname.lower()
        self.modulename = modulename
        self.package = package
        self.subpackage = sub
        self.classobject = None
    def __call__(self):
        if self.classobject is None:
            log.debug("Finding class %s.%s.%s" % (self.package, self.modulename, self.classname))
            package = ".".join([self.package, self.subpackage]) if self.subpackage else self.package
            module = __import__("%s.%s" % (package, self.modulename), fromlist=[self.classname])
            self.classobject = getattr(module, self.classname)
            log.debug("Got class %s from module %s" % (self.classobject, module))
        return self.classobject

class MultiLB(object):
    def __init__(self, *latebinds):
        self.latebinds = latebinds

    def __call__(self):
        return tuple(lb() for lb in self.latebinds)
    


    
