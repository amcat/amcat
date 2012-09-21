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
Useful methods for serialising AmCAT objects to RDF
"""

from rdflib import Graph, Namespace, Literal
import logging
log = logging.getLogger(__name__)

AMCAT = "http://amcat.vu.nl/amcat3/"
NS_AMCAT = Namespace(AMCAT)
DC = "http://purl.org/dc/elements/1.1/"
NS_DC = Namespace(DC)
XMLS = "http://www.w3.org/2001/XMLSchema#"
NS_XMLS = Namespace(XMLS)

PREDICATES = {
    ("id") : NS_DC["identifier"],
    ("name") : NS_DC["title"],
    ("insert_user") : NS_DC["creator"],
    ("Article", "headline") : NS_DC["title"],
    ("Article", "date") : NS_DC["date"],
    ("Article", "medium") : NS_DC["publisher"],
    }

from django.db.models import Model
from django.db.models.fields.related import ForeignKey

def get_uri(obj_or_class, id=None):
    if id is None:
        cls, id = obj_or_class.__class__, obj_or_class.id
    else:
        cls = obj_or_class
        
    return NS_AMCAT["{cls.__name__}/{id}".format(**locals())]


def get_predicate(model, field):
    if (model.__name__, field) in PREDICATES:
        return PREDICATES[model.__name__, field]
    if field in PREDICATES:
        return PREDICATES[field]
    return NS_AMCAT["{field}".format(**locals())]


def get_triple(obj, field):
    """
    Return rdflib subject, predicate, object triple(s) representing a value of a model or model object
    @param obj: The model instance
    @param field: the field (property) name (e.g. 'medium')
    """
    fld = obj._meta.get_field_by_name(field)[0]
    val = fld.value_from_object(obj)
    if val is None: return []
    triple_object = get_uri(fld.related.parent_model, val) if isinstance(fld, ForeignKey) else Literal(val)

    return [(
        get_uri(obj),
        get_predicate(obj.__class__, field),
        triple_object
        )]

def get_triples(obj, exclude=None):
    for field in obj._meta.fields:
        fn = field.name
        if exclude and fn in exclude:
            continue
        for t in get_triple(obj, fn):
            yield t

def serialize(triples, **options):
    """
    Serialize the given triples in the required format.
    @param options: options to be provided to rdflib.Graph.serialize. From the docs:
          destination: a file-like object, location, or None to serialize to string
          format: one of 'xml' (default), 'n3', 'turtle', 'nt', 'pretty-xml', 'trix' (or an added format)
    """
    graph = Graph()
    graph.bind("dc", DC)
    graph.bind("amcat", AMCAT)
    for triple in triples:
        graph.add(triple)
    return graph.serialize(**options)


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAmcatRDF(amcattest.PolicyTestCase):

    def test_get_triple(self):
        amcat, dc=AMCAT, DC # bring namespaces into locals
        a = amcattest.create_test_article(pagenr=12)
        s, p, o = get_triple(a, "pagenr")[0]
        self.assertEqual(unicode(s), u"{amcat}Article/{a.id}".format(**locals()))
        self.assertEqual(unicode(p), u"{amcat}pagenr".format(**locals()))
        self.assertEqual(o, a.pagenr)
        s, p, o = get_triple(a, "project")[0]
        self.assertEqual(unicode(p), u"{amcat}project".format(**locals()))
        self.assertEqual(unicode(o), u"{amcat}Project/{a.project.id}".format(**locals()))
        s, p, o = get_triple(a, "headline")[0]
        self.assertEqual(unicode(p), u"{dc}title".format(**locals()))
        self.assertEqual(o, a.headline)
        
    def test_serialize(self):
        a = amcattest.create_test_article(pagenr=12)
        triples = get_triple(a, "pagenr") + get_triple(a, "project")
        rdf = serialize(triples, format='nt')
        lines = {line for line in rdf.split("\n") if line.strip()}

        uris = dict(amcat=AMCAT, xsd="http://www.w3.org/2001/XMLSchema")
        expected_lines = {line.format(a=a, **uris) for line in [
                '<{amcat}Article/{a.id}> <{amcat}pagenr> "{a.pagenr}"^^<{xsd}#integer> .',
                '<{amcat}Article/{a.id}> <{amcat}project> <{amcat}Project/{a.project_id}> .'
                ]}

        self.assertEqual(lines, expected_lines)
                          
    def test_get_triples_project(self):
        p = amcattest.create_test_project(name=u'\x92 bla')
        triples = set(get_triples(p))
        subject = NS_AMCAT["Project/{p.id}".format(**locals())]
        for pred, obj in [
            (NS_DC["identifier"], Literal(p.id)),
            (NS_DC["creator"], NS_AMCAT["User/{p.insert_user_id}".format(**locals())]),
            ]:
            self.assertIn((subject, pred, obj), triples)


    def test_get_triples_article(self):
        from amcat.models import Article
        a = amcattest.create_test_article(headline=u'\u03a4\u1f74 \u03b3\u03bb\u1ff6\u03c3\u03c3\u03b1',
                                          date="2012-01-01")
        a = Article.objects.get(pk=a.id)

        triples = set(get_triples(a))

        subject = NS_AMCAT["Article/{a.id}".format(**locals())]
        for pred, obj in [
            (NS_DC["identifier"], Literal(a.id)),
            (NS_DC["date"], Literal(u'2012-01-01T00:00:00', datatype=NS_XMLS['dateTime'])),
            (NS_DC["title"], Literal(a.headline)),
            (NS_DC["publisher"], NS_AMCAT["Medium/{a.medium_id}".format(**locals())]),
            ]:
            self.assertIn((subject, pred, obj), triples)


    def test_get_triples_nqueries(self):
        from amcat.models import Article
        a = amcattest.create_test_article()
        with self.checkMaxQueries(1):
            a = Article.objects.get(pk=a.id)
            triples = set(get_triples(a))
            # just assert something silly to make sure we have data...
            self.assertTrue(len(triples) > 5) 
            
            
                
