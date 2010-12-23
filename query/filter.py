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

import toolkit, idlabel
from idlabel import Identity

class Filter(Identity):
    def __init__(self, concept):
        Identity.__init__(self)
        self.concept = concept
    def getValues(self):
        return None
    def getSQL(self, fieldname):
        abstract

def quotesql(val):
    if isinstance(val, idlabel.IDLabel):
        val = val.id
    return toolkit.quotesql(val)
    
        
class ValuesFilter(Filter):
    def __init__(self, concept, *values):
        Filter.__init__(self, concept)
        self.deserialized = False
        self.values = values
    def deserialize(self):
        if not self.deserialized:
            self.values = tuple(self.concept.getObject(value) for value in self.values)
            self.deserialized=True
    def getValues(self):
        self.deserialize()
        return self.values
    def getSQL(self, fieldname=None):
        if fieldname is None: fieldname = self.concept.label
        return "%s in (%s)" % (fieldname, ",".join(map(quotesql, self.values)))
    def __str__(self):
        return "%s in (%s)" % (self.concept, ",".join(map(str, self.values)))
    def identity(self):
        return self.__class__, self.concept, self.values

class IntervalFilter(Filter):
    def __init__(self, concept, fromValue=None, toValue=None):
        Filter.__init__(self, concept)
        self.fromValue = fromValue
        self.toValue = toValue
    def getSQL(self, fieldname=None):
        if fieldname is None: fieldname = self.concept.label
        fromsql = toolkit.quotesql(self.fromValue)
        tosql = toolkit.quotesql(self.toValue)
        if self.fromValue and self.toValue:
            return "%s BETWEEN %s AND %s" % (fieldname, fromsql, tosql)
        else:
            if self.fromValue:
                op, val = ">", fromsql
            else:
                op, val = "<", tosql
            return "%s %s %s" % (fieldname, op, val)
    def __str__(self):
        if self.fromValue and self.toValue:
            return "%s in (%s..%s)" % (self.concept, self.fromValue, self.toValue)
        elif self.fromValue:
            return "%s > %s" % (self.concept, self.fromValue)
        else:
            return "%s < %s" % (self.concept, self.toValue)
    def identity(self):
        return self.__class__, self.concept, self.fromValue, self.toValue
                     
