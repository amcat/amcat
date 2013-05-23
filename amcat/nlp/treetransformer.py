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
Extract semantic roles from syntax by transforming trees with SPARQL statements
"""

import logging, csv, re
from collections import namedtuple

from rdflib import Graph, Namespace, Literal

from amcat.models import Triple as TripleModel, Token
from amcat.tools import dot

log = logging.getLogger(__name__)

AMCAT = "http://amcat.vu.nl/amcat3/"
NS_AMCAT = Namespace(AMCAT)

VIS_IGNORE_PROPERTIES = "position", "label"
GOLD_ROLES = "su", "obj", "quote", "eqv", "om"

Triple = namedtuple("Triple", ["subject", "predicate","object"])

def _id(obj):
    return obj if isinstance(obj, int) else obj.id
def _token_uri(token):
    tokenstr = unicode(token).encode("ascii", "ignore")
    tokenstr = re.sub("\W", "", tokenstr)
    uri = NS_AMCAT["t_{token.position}_{tokenstr}".format(i=_id(token), **locals())]
    return uri
def _rel_uri(rel):
    return NS_AMCAT["rel_{rel}".format(**locals())]

class Node(object):
    """Flexible 'record-like' object with arbitrary attributes used for representing tokens"""
    def __unicode__(self):
        return "Node(%s)" % ", ".join("%s=%r"%kv for kv in self.__dict__.iteritems())
    def __init__(self, **kargs):
        self.__dict__.update(kargs)
    __repr__ = __unicode__

class LexicalRule(object):
    def __init__(self, lexclass, lemmata):
        self.lexclass = lexclass
        self.lemmata = lemmata
    def apply(self, transformer):
        lemmata = ",".join('"{}"'.format(l) for l in self.lemmata)
        where = '?x :lemma ?l . FILTER (?l IN ({}))'.format(lemmata)
        transformer.update(where, '?x :lexclass "{self.lexclass}"'.format(**locals()))
               
class GrammarRule(object):
    def __init__(self, where, insert, delete, name=None, show=True):
        self.where = where
        self.insert = insert
        self.delete = delete
        self.name = name
        self.show = show
    def apply(self, transformer):
        transformer.update(self.where, self.insert, self.delete)
        
def _load_lexicon(lexiconfile):
    for row in csv.DictReader(open(lexiconfile)):
        yield LexicalRule(row["class"], set(s.strip() for s in row["lemmata"].split(",")))
    
def _load_rules(rulefile):
    for row in csv.DictReader(open(rulefile)):
        if not row["active"].strip(): continue
        fields = row["where"], row["insert"], row["delete"], row["name"]
        fields = [f.decode("utf-8").replace(u"\u201c", u'"').replace(u"\u201d", u'"') for f in fields]
        fields += [bool(row["show"].strip())]
        yield GrammarRule(*fields)
        if row["show"].strip().lower() == "stop": break
    
class TreeTransformer(object):

    def __init__(self, soh, lexiconfile, rulefile, gold_roles=GOLD_ROLES):
        """
        @param soh: a amcat.tools.pysoh.SOHServer to use for transformations
        """
        self.soh = soh
        self.soh.prefixes[""] = AMCAT
        self.tokens = {} # position -> url
        self.lexicon = list(_load_lexicon(lexiconfile))
        self.rules = list(_load_rules(rulefile))
        self.gold_roles = gold_roles 

    def apply_lexical(self):
        for rule in self.lexicon:
            rule.apply(self)
        
    def apply_rules(self):
        for rule in self.rules:
            rule.apply(self)

            
    def _create_rdf_triples(self, analysis_sentence_id):
        """
        Get the raw RDF subject, predicate, object triples representing the given analysed sentence
        """
        tokenset = set()
        for t in (TripleModel.objects.filter(child__sentence = analysis_sentence_id)
                  .select_related("child", "child__word", "parent", "parent__word", "relation")):
            for pred in _rel_uri(t.relation), NS_AMCAT["rel"]:
                yield _token_uri(t.child), pred, _token_uri(t.parent)
            tokenset |= set([t.child_id, t.parent_id])

        for t in Token.objects.filter(pk__in = tokenset).select_related("word", "word__lemma"):
            uri = _token_uri(t)
            yield uri, NS_AMCAT["label"], Literal(str(t.word))
            yield uri, NS_AMCAT["lemma"], Literal(str(t.word.lemma))
            yield uri, NS_AMCAT["pos"], Literal(str(t.word.lemma.pos))
            yield uri, NS_AMCAT["position"], Literal(t.position)
            self.tokens[t.position] = uri

    def load_sentence(self, analysis_sentence_id):
        """
        Load the triples for the given analysis sentence into the triple store
        """
        # use a rdflib graph to create a serialised RDF graph - no need to create our own primitives
        g = Graph()
        g.bind("amcat", AMCAT)
        for triple in self._create_rdf_triples(analysis_sentence_id):
            g.add(triple)
        self.soh.add_triples(g, clear=True)
        log.debug("Loaded sentence {analysis_sentence_id} into SOH {self.soh}".format(**locals()))

    def get_roles(self):
        """Retrieve the childposition-role-parentposition triples"""
        for triple in self.get_triples():
            if triple.predicate not in self.gold_roles: continue
            yield Triple(int(triple.subject.position), triple.predicate, int(triple.object.position))
        read_node = lambda n : int(n) if n.strip() else None
        for s, p, o in self.query(select=["?spos", "?p", "?opos"],
                                  where="""?s ?p [:position ?opos] OPTIONAL {?s :position ?spos}
                                           FILTER (?p IN (:su, :obj, :quote, :om))"""):
            if s: s = int(s)
            if o: o = int(o)
            p = p.replace(AMCAT, "")
            if p in self.gold_roles:
                yield (s, p, o)
        
    def get_triples(self, ignore_rel=True, limit_predicate=None):
        """Retrieve the Node-predicate_string-Node triples for the loaded sentence"""
        nodes, triples = {}, []
        for s,p,o in self.soh.get_triples(parse=True):
            child = nodes.setdefault(s, Node())
            pred = str(p).replace(AMCAT, "")
            if isinstance(o, Literal):
                if hasattr(child, pred):
                    o = getattr(child, pred) + "; " + o
                setattr(child, pred, unicode(o))
            else:
                if ignore_rel and pred == "rel": continue
                if pred == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": continue
                parent = nodes.setdefault(o, Node())
                triples.append(Triple(child, pred, parent))
        # make sure every node has a position and label
        for i, n in enumerate(nodes.values()):
            set_attribute_if_missing(n, "position", -i)
            set_attribute_if_missing(n, "label", "Node_%i" % -i)
        return triples

    def update(self, where, insert="", delete=""):
        """
        Update the syntax graph with the given inserts, where and optional delete clause
        """
        self.soh.update(where, insert, delete)

    def query(self, select, where, **kargs):
        """Perform a direct query on the data store"""
        return self.soh.query(select, where, **kargs)

def set_attribute_if_missing(obj, attr, value):
    if not hasattr(obj, attr):
        setattr(obj, attr, value)

def nodes(triples):
    for triple in triples:
        for node in (triple.subject, triple.object):
            yield node

def visualise_triples(triples, triple_args_function=None,
                      ignore_properties=VIS_IGNORE_PROPERTIES):
    """
    Visualise a triples representation of Triples such as retrieved from
    TreeTransformer.get_triples
    @param triple_args_function: a function of Triple to dict that gives
                                 optional arguments for a triple
    """
    g = dot.Graph()
    nodes = {} # Node -> dot.Node
    # create nodes
    for n in set(nodes(triples)):
        label = "%s: %s" % (n.position, n.label)
        for k,v in n.__dict__.iteritems():
            if k not in ignore_properties:
                label += "\\n%s: %s" % (k, v)
        node = dot.Node(id="node_%s"%n.position, label=label)
        g.addNode(node)
        nodes[n] = node
    # create edges
    for triple in triples:
        kargs = triple_args_function(triple) if  triple_args_function else {}
        if 'label' not in kargs: kargs['label'] = triple.predicate
        g.addEdge(nodes[triple.subject], nodes[triple.object], **kargs)
    # some theme options
    g.theme.graphattrs["rankdir"] = "BT"
    g.theme.shape = "rect"
    g.theme.edgesize = 10
    g.theme.fontsize = 10

    return g


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
from amcat.tools.pysoh.test import get_test_soh

def get_test_transformer():
    return TreeTransformer(get_test_soh())

class TestGrammar(amcattest.PolicyTestCase):
    def todo_test_load(self):
        # TODO: do something useful when fuseki is not installed!
        from amcat.models import Token, Triple, Pos, Relation
        s = amcattest.create_test_analysis_sentence()
        w1, w2, w3 = [amcattest.create_test_word(word=x) for x in "abc"]
        pos = Pos.objects.create(major="x", minor="y", pos="p")
        t1 = Token.objects.create(sentence=s, position=1, word=w1, pos=pos)
        t2 = Token.objects.create(sentence=s, position=2, word=w2, pos=pos)
        rel = Relation.objects.create(label="su")
        Triple.objects.create(parent=t1, child=t2, relation=rel)

        tt = get_test_transformer()
        tt.load_sentence(s.id)

        triples = list(tt.get_triples())
        self.assertEqual(len(triples), 1)
        s,p,o = triples[0]
        self.assertEqual(p, "rel_su")
        self.assertEqual(s.label,  "b")

        tt.update("?a :rel_su []", "?a :bla 'piet'")

        triples = list(tt.get_triples())
        self.assertEqual(len(triples), 1)
        s,p,o = triples[0]
        self.assertEqual(s.bla,  "piet")

    def test_visualise(self):
        su = Node(position=1, label='piet', lemma='piet')
        obj = Node(position=2, label='slaapt', lemma='slaap')
        g = visualise_triples([Triple(su, "su", obj)])
        self.assertEqual(len(g.edges), 1)
        edge = g.edges.values()[0][0]
        self.assertEqual(edge.subj.label, "1: piet\\nlemma: piet")
        self.assertEqual(edge.label, "su")
        taf = lambda triple: dict(color=dict(su='red', obj1='blue')[triple.predicate])

        g = visualise_triples([Triple(su, "su", obj), Triple(obj, "obj1", su)], taf)
        e1, e2 = g.edges.values()[0][0], g.edges.values()[1][0]
        self.assertEqual(set([e1.color, e2.color]), set(["red", "blue"]))
