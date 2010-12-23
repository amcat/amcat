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

import datasource
import toolkit
from datamodel import Concept

class State(object):
    """
    The State of the data tabulation/aggregation algorithm consisting of
    Nodes and Edges. Initially, Nodes and Edges correspond to Fields and Mappings,
    but as Operations are applied the state is reduced by combining different Nodes
    to form Nodes consisting of multiple Fields. 
    """
    def __init__(self, tabulator, mappings, filters, distinct=False):
        """
        mappings is a list of Mapping objects representing the initial state
        filters {field: list-of-values} are seen as a priori data structures on the nodes
        distinct is a boolean representing whether distinct values are required
        """
        self.tabulator = tabulator
        self.distinct = distinct
        if mappings:
            self.edges = set(mappings2edges(mappings, filters))
            self.solution = None
        else:
            if len(filters) != 1:
                raise Exception("Multiple or lack of filters not supported.")
            f = toolkit.head(filters)
            values = f.getValues()
            if values is None:
                raise Exception("Values is None.")
            self.solution = Node([f.concept], [(v,) for v in values], f)

    def collapse(self, oldedges, newnode):
        """
        Removes the given Edge oldedge from this state, replacing its nodes
        by the given Node newnode. Removing the last edge will set the solution
        variable to the data of the newnode.
        """
        oldedges = set(oldedges)

        self.edges -= oldedges
        if not self.edges or not newnode.data:
            self.solution = newnode
        else: # Replace references to old nodes, by reference to new node
            oldnodes = []
            for edge in oldedges:
                oldnodes += [edge.a, edge.b]
            for edge in self.edges:
                if edge.a in oldnodes:
                    edge.a = newnode
                if edge.b in oldnodes:
                    edge.b = newnode
        if self.tabulator:
            self.tabulator.clean(self, newnode)
    def getNodes(self):
        nodes = set()
        for edge in self.edges: nodes |= set([edge.a, edge.b])
        return nodes
    def getEdges(self, fromnode):
        for edge in self.edges:
            if edge.a == fromnode:
                yield edge
    def __len__(self):
        return len(self.edges)    


def mappings2edges(mappings, filters):
    filters = dict((f.concept, f) for f in filters) # cache concept -> filter
    nodes = {} # temp field -> Node map
    def getNode(field):
        if field not in nodes:
            filter = filters.get(field)
            values = filter.getValues() if filter else None
            data = [[x] for x in values] if values else None
            nodes[field] = Node([field], data, filter)
        return nodes[field]
    for mapping in mappings:
        nodea = getNode(mapping.a)
        nodeb = getNode(mapping.b)

        for a,b in ([nodea,nodeb], [nodeb,nodea]):
            if isinstance(a.fields[0], Concept) and a.filter and not a.data:
                b.filter = a.filter

        yield Edge(nodea, nodeb, mapping)

class Node(object):
    """
    Class Node contains a list of Field objects and a list of data
    A Node is connected to other nodes by NodeMappings
    """
    def __init__(self, fields, data, filter=None):
        self.fields = fields # list of Field objects
        self.data = data # list of tuple of data
        self.filter = filter
    def getFields(self):
        return self.fields
    def  __str__(self):
        return "Node(%r, %r)" % (self.fields, self.data)
    __repr__ = __str__

class Edge(object):
    """
    An edge is an edge between two Nodes, corresponding to a mapping between fields in these nodes 
    """
    def __init__(self, a, b, mapping):
        """create an Edge between nodes 'a' and 'b' corresponding to the given mapping
        This fields of this mapping should exist in the Nodes a and b"""
        self.a = a
        self.b = b
        self.mapping = mapping
    def __str__(self):
        return "Edge(%r,%r)" % (self.a, self.b)
    __repr__ = __str__
            
