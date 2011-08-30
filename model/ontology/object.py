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

from django.db import models

from amcat.tools.model import AmcatModel
from amcat.tools import toolkit
from amcat.model.language import Language
from amcat.model.ontology.tree import Tree

from datetime import datetime

import logging; log = logging.getLogger(__name__)

PARTYMEMBER_FUNCTIONID = 0


# def strmaker():
    # return lambda obj, val: val
    
class Object(AmcatModel):
    id = models.IntegerField(primary_key=True, db_column='object_id')
    
    #functions = ForeignKey(Function) # TODO: create reverse in Function for this
    trees  = models.ForeignKey(Tree, table="trees_objects", distinct=True)

    labels = models.ForeignKey(Language,
                         table="labels", getcolumn=("languageid", "label"),
                         sequencetype=dict)

    name = DBProperty(table="o_politicians")
    firstname = DBProperty(table="o_politicians")
    prefix = DBProperty(table="o_politicians")
    initials = DBProperty(table="o_politicians")

    class Meta():
        db_table = 'objects'

    @property
    def label(self):
        lang = toolkit.head(sorted(self.labels.keys()))
        if lang: return self.labels[lang]
        return repr(self)

    def getLabel(self, lan, fallback=True):
        """
        @param lan: language to get label for
        @type lan: integer or Language object
        """
        if not hasattr(lan, 'id'):
            lan = Language(self.db, lan)
        
        if self.labels.has_key(lan):
            return self.labels[lan]
    	
        if fallback:
          return self.label

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
        
    def currentFunctions(self, date=None, party=None):
        """Yield the current functions of the politician
        @param date: the date for 'current' (default: now)
        @param party: if None, yield both membership and functions. If True,
          yield only party membership. If False, yield only other functions
        """
        if not date: date = datetime.now()
        date = toolkit.toDate(date)
        for f in self.functions:
            # check date condition
            fd = toolkit.toDate(f.fromdate)
            if (date - fd).days < 0: continue # fromdate after 'now'
            if f.todate:
                td = toolkit.toDate(f.todate)
                if (td - date).days < 0: continue # todate before 'now'

            # check party condition
            if party is not None:
                if bool(party) != bool(f.party):
                    continue
            yield f

    def getParty(self, date=None):
        r = toolkit.head(self.currentFunctions(date, party=True))
        return r and r.office
    
            
    def getSearchString(self, date=None, xapian=False, languageid=None, fallback=False):
        """Returns the search string for this object.
        date: if given, use only functions active on this date
        xapian: if true, do not use ^0 weights
        languageid: if given, use labels.get(languageid) rather than keywords"""

        
        if not date: date = datetime.now()
        kw = self.getLabel(languageid, fallback=False)

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

            
class Function(AmcatModel):
    object = models.ForeignKey(Object)

    functionid = models.SmallIntegerField()
    fromdate = models.DateField()
    todate = models.DateField()

    office = models.ForeignKey(Object, db_column='office_object_id')

    def __unicode__(self):
        return self.office

    class Meta():
        db_table = 'objects_functions'
        app_label = 'ontology'
        unique_together = ("objectid", "functionid", "office_objectid", "fromdate")
    
    
def function2conds(function):
    officeid = function.office.id
    if officeid in (380, 707, 729, 1146, 1536, 1924, 2054, 2405, 2411, 2554, 2643):
        if function.functionid == 2:
            return ["bewinds*", "minister*"]
        else:
            return ["bewinds*", "staatssecret*"]

    if officeid == 901:
        return ["premier", '"minister president"']
    if officeid == 548:
        return ["senator", '"eerste kamer*"']
    if officeid == 1608:
        return ["parlement*", '"tweede kamer*"']
    if officeid == 2087:
        return ['"europ* parlement*"', "europarle*"]
    return []
