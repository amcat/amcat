from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.tools.cachable.latebind import LB

from amcat.tools import toolkit
from amcat.model.language import Language

from amcat.model.ontology.ontologytoolkit import getParent

from datetime import datetime

import logging; log = logging.getLogger(__name__)

class Function(Cachable):
    __table__ = "objects_functions"
    __idcolumn__ = ("functionid", "office_objectid", "fromdate")
    
    functionid, todate = DBProperties(2)
    _fromdate = DBProperty(getcolumn="fromdate")
    office = DBProperty(lambda : Object, refcolumn="office_objectid")
    
    @property
    def fromdate(self):
        if self._fromdate.year != 1753:
            return self._fromdate
        
    @property
    def klass(self):
        return Class(db, 1) if self.functionid==0 else Class(db, 2)
    
class Label(Cachable):
    __table__ = 'labels'
    __idcolumn__ = ('objectid', 'languageid')
    
    label, objectid, languageid = DBProperties(3)
    
    language = DBProperty(LB("Language"))
    
class Object(Cachable):
    __table__ = 'objects'
    __idcolumn__ = 'objectid'
    
    _labels = ForeignKey(lambda:Label)
    _parents = ForeignKey(table="trees_objects", getcolumn=("treeid", "parentid"), refcolumn="objectid", constructor=getParent)
    _children = ForeignKey(table="trees_objects", getcolumn=("treeid", "objectid"), refcolumn="parentid", constructor=getParent)

    @property
    def labels(self):
        return dict((l.language, l.label) for l in self._labels)
    
    @property
    def parents(self):
        return dict(self._parents)
    
    @property
    def children(self):
        return toolkit.multidict(self._children)
    
    @property
    def label(self):
        try:
            return self._labels.next().label
        except StopIteration:
            return 'GEEN LABEL: FIXME'

    def getLabel(self, lan):
        """
        @param lan: language to get label for
        @type lan: integer or Language object
        """
        
        if not hasattr(lan, 'id'):
            lan = Language(self.db, lan)

        if self.labels.has_key(lan): return self.labels[lan]
    
    # Move to separate class?
    #name = DBProperty(table="politicians")
    #firstname = DBProperty(table="politicians")
    #prefix = DBProperty(table="politicians")
    #keyword = DBProperty(table="keywords")
    #male = DBProperty(table="politicians")
    
    functions = ForeignKey(lambda:Function)

    def getAllParents(self, date=None):
        for c, p in self.parents.iteritems():
            yield c, p
        for f in self.currentFunctions(date):
            yield f.klass, f.office
        
    def currentFunctions(self, date=None):
        if not date: date = datetime.now()
        for f in self.functions:
            if f.fromdate and toolkit.cmpDate(date, f.fromdate) < 0: continue
            if f.todate and toolkit.cmpDate(date, f.todate) >= 0: continue
            yield f
    
    def getSearchString(self, date=None, xapian=False, languageid=None, fallback=False):
        """Returns the search string for this object.
        date: if given, use only functions active on this date
        xapian: if true, do not use ^0 weights
        languageid: if given, use labels.get(languageid) rather than keywords"""
        
        if not date: date = datetime.now()
        if languageid:
            kw = self.getLabel(languageid)

        if (not languageid) or (fallback and kw is None):
            kw = self.keyword
        
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
