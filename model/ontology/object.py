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

"""
Model module representing ontology Objects
"""

from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.tools.cachable.latebind import LB, MultiLB

from amcat.tools import toolkit
from amcat.model.language import Language


from datetime import datetime

import logging; log = logging.getLogger(__name__)

class Function(Cachable):
    __table__ = "objects_functions"
    __idcolumn__ = ("objectid", "functionid", "office_objectid", "fromdate")
    
    functionid, todate, fromdate = DBProperties(3)
    office = DBProperty(lambda : Object, refcolumn="office_objectid")
    
class Label(Cachable):
    __table__ = 'labels'
    __idcolumn__ = ('objectid', 'languageid')
    
    label, objectid, languageid = DBProperties(3)
    
    language = DBProperty(LB("Language"))

    
class Object(Cachable):
    __table__ = 'objects'
    __idcolumn__ = 'objectid'
    
    _labels = ForeignKey(Label)
    functions = ForeignKey(Function)
    trees  = ForeignKey(LB("Tree", sub="ontology"), table="trees_objects", distinct=True)

    @property
    def labels(self):
        return dict((l.language, l) for l in self._labels)
    
    @property
    def label(self):
        l = toolkit.head(self._labels)
        if l: return l
        return repr(self)

    def getLabel(self, lan):
        """
        @param lan: language to get label for
        @type lan: integer or Language object
        """
        
        if not hasattr(lan, 'id'):
            lan = Language(self.db, lan)

        if self.labels.has_key(lan): return self.labels[lan]


    def _getTree(self, treeid):
        for t in self.trees:
            if t.id == treeid: return t

    def getParent(self, tree):
        if type(tree) == int: tree = self._getTree(tree)
        return tree.getParent(self)

    @property
    def parents(self):
        for t in self.trees:
            yield t, self.getParent(t)
    
    def getAllParents(self, date=None):
        for c, p in self.parents.iteritems():
            yield c, p
        for f in self.currentFunctions(date):
            yield f.klass, f.office
        
    def currentFunctions(self, date=None):
        if not date: date = datetime.now()
        for f in self.functions:
            fd = f.fromdate
            td = f.todate or datetime.now()

            tdf = (date - fd).days
            tdt = (td - date).days

            if tdf >= 0 and tdt >= 0: yield f

    def getSearchString(self, date=None, xapian=False, languageid=None, fallback=False):
        """Returns the search string for this object.
        date: if given, use only functions active on this date
        xapian: if true, do not use ^0 weights
        languageid: if given, use labels.get(languageid) rather than keywords"""
        
        if not date: date = datetime.now()
        kw = self.getLabel(languageid)

        #if (not languageid) or (fallback and kw is None):
        #    kw = self.keyword
        
        if not kw and self.name:
            ln = self.name
            if "-" in ln or " " in ln:
                ln = '"%s"' % ln.replace("-", " ")
            conds = []
            if self.firstname:
                conds.append(self.firstname)
            for function in self.currentFunctions(date):
                k = function.office.getSearchString()
                if not k: k = '"%s"' % str(function.office).replace("-"," ")
                conds.append(k)
                conds += function2conds(function)
            if conds:
                if xapian:
                    kw = "%s AND (%s)" % (ln, " OR ".join("%s" % x.strip() for x in conds),)
                else:
                    kw = "%s AND (%s)" % (ln, " OR ".join("%s^0" % x.strip() for x in conds),)
            else:
                kw = ln
        if kw:
            if type(kw) == str: kw = kw.decode('latin-1')
            return kw.replace("\n"," ")
