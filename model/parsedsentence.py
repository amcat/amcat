
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
Model module containing the classes representing the parses_* tables
"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.tools.cachable.cachable import Cachable, DBProperty, ForeignKey, DBProperties
from amcat.tools.cachable.latebind import LB
from amcat.tools import graph
from amcat.model import sentence, analysis

class ParsedSentence(Cachable, graph.Graph):
    # NO table, there is no specific table for parsed sentences!
    __idcolumn__ = ('sentenceid', 'analysisid')

    triples = ForeignKey(lambda: ParsedTriple)
    words = ForeignKey(lambda : ParsedWord) #orderby

    def getWord(self, position):
        for word in self.words:
            if word.position == position: return word
            
    @property
    def sentence(self):
        from amcat.model import sentence
        return sentence.Sentence(self.db, self.id[0])
    @property
    def analysis(self):
        from amcat.model import analysis
        return analysis.Analysis(self.db, self.id[1])
    def getTriples(self):
        for triple in self.triples:
            yield triple.parent, triple.relation, triple.child


class ParsedWord(graph.Node, Cachable):
    __table__ = 'parses_words'
    __idcolumn__ = ['sentenceid','analysisid','wordbegin']
    __labelprop__ = 'word'
    word = DBProperty(LB("Word"))
    posid = DBProperty()

    
    def __init__(self, *args, **kargs):
        Cachable.__init__(self, *args, **kargs)
        graph.Node.__init__(self)
        
    @property
    def position(self):
        return self.id[2]
    @property
    def sentence(self):
        return sentence.Sentence(self.db, self.id[0])
    @property
    def parsedSentence(self):
        return ParsedSentence(self.db, *self.id[:2])
    def getGraph(self):
        "Implement graph.Node.getGraph by returning the parse tree of the sentence"
        return self.parsedSentence

    def __str__(self):
        return "%i:%s" % (self.position, self.word)
    
    def getNeighbour(self, offset=1):
        return self.sentence.getWord(self.position + offset)


class Relation(Cachable):
    __table__ = "parses_rels"
    __idcolumn__ = "relid"
    __dbproperties__ = ["name"]
    __labelprop__ = 'name'
    name = DBProperty()
    
class ParsedTriple(Cachable):
    __table__ = 'parses_triples'
    __idcolumn__ = 'sentenceid','analysisid','childbegin','parentbegin'
    relation = DBProperty(Relation, getcolumn="relation")
    #parentbegin = DBProperty()


    @property
    def child(self):
        return ParsedWord(self.db, *self.id[:3])
    @property
    def parent(self):
        sid, aid, c, p = self.id
        return ParsedWord(self.db, sid, aid, p)
        
    @property
    def parsedSentence(self):
        return ParsedSentence(self.db, *self.id[:2])
    @property
    def analysis(self):
        return analysis.Analysis(self.db, self.id[1])
    
if __name__ == '__main__':
    from amcat.db import dbtoolkit
    db = dbtoolkit.amcatDB()
    ps = ParsedSentence(db, 51280986, 2)
    #for triple in ps.triples:
    #    print(triple)


    pw = ParsedWord(db, 51280986, 2, 4)
    for child in pw.children:
        print(child)
