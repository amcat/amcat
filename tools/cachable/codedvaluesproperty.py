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
Property that links to coded values in a table that depends on the coding
schema.
"""

from __future__ import unicode_literals, print_function, absolute_import
from amcat.tools.cachable.cachable import Property
from collections import namedtuple, defaultdict

import logging; log = logging.getLogger(__name__)
from amcat.tools.logging import amcatlogging
amcatlogging.debugModule()

class _CodedValuesSchemaSupport(object):
    def __init__(self, schema):
	self.schema = schema
	self.fields = list(schema.fields)
	self.fieldnames = [f.fieldname for f in self.fields]
	self.nt = namedtuple("values_%i" % self.schema.id, self.fieldnames)

    def retrieve(self, obj):
	idcol = "codingjob_articleid" if self.schema.isarticleschema else "codedsentenceid"
	#log.debug("Retrieving %s from %s for %s : %s" % (self.fieldnames, self.schema.table, self.schema.id, obj.id))
	result = obj.db.select(self.schema.table, self.fieldnames, {idcol : obj.id})
	if not result: return None
	return result[0]

    def retrievemany(self, db, property, objects):
	idcol = "codingjob_articleid" if self.schema.isarticleschema else "codedsentenceid"
	objectsperid = {}
	oids = []
	for obj in objects:
	    objectsperid[obj.id] = obj
	    oids.append(obj.id)
	    
	data =  db.select(self.schema.table, [idcol] + self.fieldnames, {idcol : oids})
	for row in data:
	    id, row = row[0], row[1:]
	    property.cache(objectsperid[id], row)

    def dataToObjects(self, data):
	des = [f.deserialize(v) for (f,v) in zip(self.fields, data)]
	return self.nt(*des)

class CodedValuesProperty(Property):

    def __init__(self, schemahook):
	Property.__init__(self)
	self.schemahook = schemahook
	self.schemas = {}

    def _getSchemaSupport(self, obj):
	schema = self.schemahook(obj)
	try:
	    return self.schemas[schema]
	except KeyError:
	    s = _CodedValuesSchemaSupport(schema)
	    self.schemas[schema] = s
	    return s

    def retrieve(self, obj):
	s = self._getSchemaSupport(obj)
	return s.retrieve(obj)

    def dataToObjects(self, obj, data):
	s = self._getSchemaSupport(obj)
	return s.dataToObjects(data)
	
    def cachePerObject(self, db, objects):
	objectsperschema = defaultdict(set)
	for obj in objects:
	    s = self._getSchemaSupport(obj)
	    objectsperschema[s].add(obj)
	    
	for schemasupport, objects in objectsperschema.iteritems():
	    schemasupport.retrievemany(db, self, objects)
	    
	
    
