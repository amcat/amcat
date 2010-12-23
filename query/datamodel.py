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

from idlabel import IDLabel
import collections

class Concept(IDLabel):
    """ 
    Concept represents the concepts in the datamodel. The concepts can be used to create mappings between datasources.
    """
    def __init__(self, datamodel, label, id):
        IDLabel.__init__(self, id, label)
        self.datamodel = datamodel
    def getObject(self, id):
        return self.datamodel.deserialize(self, id)
    def __repr__(self):
        return "Concept(%s)" % self.label

    

# TODO: identifier -> id (list index) mapping for concepts. This is pretty ugly and should be either decentralized
#       (but we need to guarantee consistency across datasources/models) or put into database?
CONCEPTS = ["article", "batch", "headline",  "date", "week", "year", "source", "url", "project", "sourcetype", "storedresult", "sentiment", "search", "brand", "property", "brandproperty", "associationcooc", "customer", "propertycluster", "actor", "issue", "issuearticle", "coocissue", "issuecooc", "set", "subject", "object", "arrow", "quality"]

class DataModel(object):
    """ 
    The datamodel contains all the datasources, 
    which in their turn contain fields and concepts that can be either mapped or not. 
    """
    def __init__(self, datasources = None):
        self._datasources = datasources or set()
        self._concepts = {} # identifier -> concept
        for id, label in enumerate(CONCEPTS):
            c =  Concept(self, label, id)
            self._concepts[label] = c
            self.__dict__[label] = c

    def deserialize(self, concept, identifier):
        for datasource in self._datasources:
            obj = datasource.deserialize(concept, identifier)
            if obj: return obj
        return identifier

    def register(self, datasource):
        self._datasources.add(datasource)

    def getConcept(self, identifier):
        if isinstance(identifier, Concept): identifier = identifier.label
        if isinstance(identifier, int): identifier = CONCEPTS[identifier]
        return self._concepts[identifier]

    def getConcepts(self):
        return self._concepts.values()

    def getMappings(self):
        for datasource in self._datasources:
            for mapping in datasource.getMappings():
                yield mapping
        for mapping in self._getFieldConceptMappings():
            yield mapping

    def _getFieldConceptMappings(self):
        fieldmap = collections.defaultdict(set) # concept : 1..n field
        for datasource in self._datasources:
            for mapping in datasource.getMappings():
                for field in mapping.a, mapping.b:
                    fieldmap[field.concept].add(field)
        for concept, fields in fieldmap.items():
            for field in fields:
                yield field.getConceptMapping()
        
