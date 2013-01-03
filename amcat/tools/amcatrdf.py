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

from amcat.models import CodebookCode, Code, CodingJob
from amcat.tools.toolkit import set_closure

log = logging.getLogger(__name__)

AMCAT = "http://amcat.vu.nl/amcat3/"
NS_AMCAT = Namespace(AMCAT)
DC = "http://purl.org/dc/elements/1.1/"
NS_DC = Namespace(DC)
XMLS = "http://www.w3.org/2001/XMLSchema#"
NS_XMLS = Namespace(XMLS)
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
NS_RDFS = Namespace(RDFS)
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
NS_RDF = Namespace(RDF)

NAMESPACES = dict(amcat=AMCAT, dc=DC, xmls=XMLS, rdfs=RDFS, rdf=RDF)

PREDICATES = {
    ("id") : NS_DC["identifier"],
    ("name") : NS_DC["title"],
    ("label") : NS_DC["title"],
    ("insert_user") : NS_DC["creator"],
    ("insertuser") : NS_DC["creator"],
    ("insert_date") : NS_DC["date"],
    ("insertdate") : NS_DC["date"],
    ("Article", "headline") : NS_DC["title"],
    ("Article", "date") : NS_DC["date"],
    ("Article", "medium") : NS_DC["publisher"],
    ("Article", "length") : None, # computable
    ("isnet") : None,
    ("quasisentences") : None,
    ('Project', 'guest_role') : None,
    ('Project', 'active') : None,
    ('CodingJob', 'articleset') : NS_DC["subject"],
    ('CodingJob', 'unitschema') : None, # TODO: something useful with this
    ("ArticleSet", "batch") : None, # deprecated
    ("ArticleSet", "codingjobset") : None, # computable
    }

CODE_HIDE = NS_AMCAT["code_constant_hide"]
CODE_ROOT = NS_AMCAT["code_constant_root"]

RDFS_LABEL = NS_RDFS["label"]
RDFS_SUBPROP = NS_RDFS["subPropertyOf"]


from django.db.models.fields.related import ForeignKey

def get_uri(obj_or_class, object_id=None):
    """Get the uri for an object
    If first argument is a class, second argument should be the instance id
    (this allows uri to be generated without creating an instance (e.g. without a db roundtrip)
    """
    if object_id is None:
        _cls, object_id = obj_or_class.__class__, obj_or_class.id
    else:
        _cls = obj_or_class
        
    return NS_AMCAT["{_cls.__name__}/instance_{object_id}".format(**locals())]


def get_predicate(model, field):
    """
    Get the predicate corresponding to the field.
    Return a DC predicate if available or a default one if not.
    """
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
    triple_object = (get_uri(fld.related.parent_model, val)
                     if isinstance(fld, ForeignKey) else Literal(val))

    predicate = get_predicate(obj.__class__, field)
    if predicate is None: return []
    return [(
        get_uri(obj),
        predicate,
        triple_object
        )]

def get_triples(obj, exclude=None):
    """
    Get the triples for an object obj, giving a triple for each attribute
    @param exclude: if given, a list of attribute names to be excluded
    """
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
    for name, ns in NAMESPACES.items():
        graph.bind(name, ns)
    # Bind 'subspaces' to allow use in attributes
    graph.bind('amcatcodingschemafield', AMCAT + 'CodingSchemaField/')
    graph.bind('amcatcodebook', AMCAT + 'Codebook/')


    for triple in triples:
        graph.add(triple)
    return graph.serialize(**options)

def get_triples_project(project):
    """
    Generate the triples for a project an all contents
    """
    triples = []
    triples += list(get_triples(project))

    for art in project.all_articles():
        triples += list(get_triples(art))

    for aset in project.articlesets.all():
        triples += list(get_triples_articleset(aset))
        
    for schema in project.get_codingschemas():
        triples += list(get_triples_schema(schema))

    codebooks = set_closure(project.get_codebooks(), lambda c: c.bases)
    triples += list(get_triples_codebooks(codebooks))

    for job in CodingJob.objects.filter(project=project):
        triples += list(get_triples_codingjob(job))
    
    return triples

def get_triples_articleset(aset):
    """
    Generate the triples for an article set including which articles are in it
    (but the articles are not serialized as they can occur in more than one set)
    """
    for triple in get_triples(aset):
        yield triple
    for article in aset.articles.all():
        yield get_uri(aset), NS_RDF["li"], get_uri(article)
        
def get_triples_schema(schema):
    """
    Generate the triples for a schema including fields
    """
    for triple in get_triples(schema):
        yield triple
    for field in schema.fields.all():
        for triple in get_triples(field, exclude=["fieldtype"]):
            yield triple
        yield (get_uri(field), get_predicate(field.__class__, "fieldtype"), Literal(field.fieldtype.name))

def get_triples_codingjob(job):
    for triple in get_triples(job):
        yield triple
    for coding in job.codings.all():
        for triple in get_triples_coding(coding):
            yield triple
        

def get_triples_codebooks(codebooks):
    """
    Generate the triples for a set of codebooks.
    This is a special case because we would like the result to be interpretable as a
    'normal' rdf taxonomy. 
    """
    codebook_codes = CodebookCode.objects.filter(codebook__in=codebooks)

    # serialize nodes
    for cc in codebook_codes:
        codebook_uri = get_uri(cc.codebook)
        code_uri = get_uri(cc._code)
        if cc.hide:
            target = CODE_HIDE
        elif cc._parent is None:
            target = CODE_ROOT
        else:
            target = get_uri(cc._parent)
        yield (code_uri, codebook_uri, target)

    # serialize labels and code-attributes
    for c in set(cc._code for cc in codebook_codes):
        for triple in get_triples(c): yield triple
        for l in c.labels.all():
            yield (get_uri(c), RDFS_LABEL, Literal(l.label, lang=l.language))

    # serialize bases and codebook-attributes
    for cb in codebooks:
        for triple in get_triples(cb): yield triple
        for base in cb.bases:
            yield (get_uri(cb), RDFS_SUBPROP, get_uri(base))

def get_triples_coding(coding):
    """
    Generate the triples for a coding
    This is a special case because the values are directly included, and the
    dc:subject is set to the article or sentence as needed
    """
    for triple in get_triples(coding, exclude={"article","sentence"}):
        yield triple

    subject = coding.article if coding.sentence is None else coding.sentence
    yield get_uri(coding), NS_DC["subject"], get_uri(subject)

    for field, value in coding.get_values():
        if isinstance(value, (str, int, bool, float)):
            object = Literal(value)
        elif isinstance(value, Code):
            object = get_uri(value)
        else:
            raise TypeError("Cannot deal with values {value!r}".format(**locals()))
        yield get_uri(coding), get_uri(field), object
    
            

def _print_triples(triples):
    """Print a triple (for debug purposes)"""
    def _node2str(node):
        """Convert a uri or literal into a concise representation"""
        s = unicode(node)
        if isinstance(node, Literal):
            s= u'"{s}"'.format(**locals())
            if node.language:
                s += u'^^{node.language}'.format(**locals())
        else:
            for abbrev, full in NAMESPACES.items():
                s = s.replace(full, u"{abbrev}:".format(**locals()))
        return s
    for triple in triples:
        print (u"%s -(%s)-> %s" % tuple(_node2str(x) for x in triple)).encode("utf-8")

    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAmcatRDF(amcattest.PolicyTestCase):
    PYLINT_IGNORE_EXTRA = ['W0212'] # protected members _meta and _code/_parent
                                    # TODO: latter should be removed after refactoring codebook

    def setUp(self):
        """Populate a project with articles, coding etc"""
        from amcat.models import Language, Project, Article
        
        self.project = amcattest.create_test_project()

        # create a codebook
        self.codebook = amcattest.create_test_codebook(project=self.project, name="base codebook")
        en = Language.objects.get(label='en')    
        sv = Language.objects.create(label='sv')
        _cargs = dict(language=en, codebook=self.codebook)
        self.code_a = amcattest.create_test_code(label="a", **_cargs)
        self.code_a.add_label(label=u"\xe5", language=sv)
        self.code_b = amcattest.create_test_code(label="b", parent=self.code_a, **_cargs)
        self.code_c = amcattest.create_test_code(label="c", parent=self.code_a, **_cargs)
       
        self.sub_codebook = amcattest.create_test_codebook(project=self.project, name="sub codebook")
        self.sub_codebook.add_base(self.codebook)
        self.code_d = amcattest.create_test_code(label="d", language=en,
                                                 codebook=self.sub_codebook, parent=self.code_a)
        CodebookCode.objects.create(codebook=self.sub_codebook, _code=self.code_c, hide=True)
        CodebookCode.objects.create(codebook=self.sub_codebook, _code=self.code_b, _parent=None)

        # create a schema
        self.schema, _dummy, self.strfield, self.intfield, self.codefield = (
            amcattest.create_test_schema_with_fields(project=self.project, codebook=self.sub_codebook))

        self.article_hl = u'The great wall of China (\u9577\u57ce)'
        self.article_text = u"""This is some text with greek characters\n
                               \u03bc\u1fc6\u03bd\u03b9\u03bd \u1f04\u03b5\u03b9\u03b4\u03b5,
                               \u03b8\u03b5\u03ac,
                               \u03a0\u03b7\u03bb\u03b7\u03ca\u03ac\u03b4\u03b5\u03c9
                               \u1f08\u03c7\u03b9\u03bb\u1fc6\u03bf\u03c2"""
        self.article = amcattest.create_test_article(headline=self.article_hl, project=self.project,
                                                     text=self.article_text, date="2012-01-01")
        self.article = Article.objects.get(pk=self.article.id) # to get date redeserialized
        
        self.articleset = amcattest.create_test_set(project=self.project)
        self.articleset.add(self.article)
        
        self.job = amcattest.create_test_job(project=self.project, articleset=self.articleset,
                                             unitschema=self.schema, articleschema=self.schema)
        
        self.coding = amcattest.create_test_coding(codingjob=self.job, comments="Obvious", article=self.article)
        self.coding.update_values({self.strfield:"abc", self.intfield:1, self.codefield:self.code_d})
       
    def test_serialize(self):
        """Does serializing to nt bytes work?"""
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

    def test_get_triple(self):
        """Do we get the right triple, esp. with the right uri and predicate?"""
        _amcat, _dc = AMCAT, DC # bring namespaces into locals
        a = amcattest.create_test_article(pagenr=12)
        s, p, o = get_triple(a, "pagenr")[0]
        self.assertEqual(unicode(s), u"{_amcat}Article/{a.id}".format(**locals()))
        self.assertEqual(unicode(p), u"{_amcat}pagenr".format(**locals()))
        self.assertEqual(o, a.pagenr)
        s, p, o = get_triple(a, "project")[0]
        self.assertEqual(unicode(p), u"{_amcat}project".format(**locals()))
        self.assertEqual(unicode(o), u"{_amcat}Project/{a.project.id}".format(**locals()))
        s, p, o = get_triple(a, "headline")[0]
        self.assertEqual(unicode(p), u"{_dc}title".format(**locals()))
        self.assertEqual(o, a.headline)
        
    def _expected_triples_codebook(self):
        from amcat.models import Language, Project
        u, cb, a, b, c  = get_uri, self.codebook, self.code_a, self.code_b, self.code_c
        en = Language.objects.get(label='en')    
        sv = Language.objects.get(label='sv')
        return {
            # hierarchy
            (u(a), u(cb), CODE_ROOT),
            (u(b), u(cb), u(a)),
            (u(c), u(cb), u(a)),
            # labels
            (u(a), RDFS_LABEL, Literal("a", lang=en)),
            (u(a), RDFS_LABEL, Literal(u"\xe5", lang=sv)),
            (u(b), RDFS_LABEL, Literal("b", lang=en)),
            (u(c), RDFS_LABEL, Literal("c", lang=en)),
            # code-attributes (id) and codebook attributes
            (u(a), PREDICATES["id"], Literal(a.id)),
            (u(b), PREDICATES["id"], Literal(b.id)),
            (u(c), PREDICATES["id"], Literal(c.id)),
            (u(cb), PREDICATES["id"], Literal(cb.id)),
            (u(cb), NS_AMCAT["project"], u(Project, cb.project_id)),
            (u(cb), PREDICATES["name"], Literal(cb.name)),
            }

    def _expected_triples_sub_codebook(self):
        from amcat.models import Language
        u, cb, sub =get_uri, self.codebook, self.sub_codebook
        a, b, c, d= self.code_a, self.code_b, self.code_c, self.code_d
        en = Language.objects.get(label='en') 
        

        u = get_uri
        return {(u(sub), RDFS_SUBPROP, u(cb)),
                (u(d), RDFS_LABEL, Literal("d", lang=en)),
                (u(d), u(sub), u(a)),
                (u(c), u(sub), CODE_HIDE),
                (u(b), u(sub), CODE_ROOT),
                } | set(get_triples(sub)) | set(get_triples(d))
        
        return sub, triples_sub

    def _expected_triples_schema(self):
        from amcat.models import Project
        u = get_uri
        schema = self.schema
        result =  {(u(schema), PREDICATES["id"], Literal(schema.id)),
                   (u(schema), PREDICATES["name"], Literal(schema.name)),
                   (u(schema), NS_AMCAT["isarticleschema"], Literal(False)),
                   (u(schema), NS_AMCAT["project"],  u(Project, self.project.id)),
                   }
        for field in schema.fields.all():
            result |= {(u(field), PREDICATES["id"], Literal(field.id)),
                       (u(field), NS_AMCAT["codingschema"], u(schema)),
                       (u(field), NS_AMCAT["fieldnr"], Literal(field.fieldnr)),
                       (u(field), PREDICATES["name"], Literal(field.label)),
                       (u(field), NS_AMCAT["required"], Literal(field.required)),
                       (u(field), NS_AMCAT["fieldtype"], Literal(field.fieldtype.name)),
                       }
            if field.codebook:
                result |= {(u(field), NS_AMCAT["codebook"], u(self.sub_codebook))}
        return result

    def _expected_triples_coding(self):
        u, c = get_uri, self.coding
        return {
            # coding attributes
            (u(c), NS_DC["subject"], u(c.article)),
            (u(c), PREDICATES["id"], Literal(c.id)),
            (u(c), NS_AMCAT["codingjob"], u(self.job)),
            (u(c), NS_AMCAT["comments"], Literal("Obvious")),
            (u(c), NS_AMCAT["status"], u(c.status)),
            # coding values 
            (u(c), u(self.strfield), Literal("abc")),
            (u(c), u(self.intfield), Literal(1)),
            (u(c), u(self.codefield), u(self.code_d)),
            }

    def _expected_triples_project(self):
        u, p = get_uri, self.project
        return {(u(p), PREDICATES["id"], Literal(p.id)),
                (u(p), PREDICATES["name"], Literal(p.name)),
                (u(p), NS_DC["creator"], u(p.insert_user)),
                (u(p), NS_AMCAT["owner"], u(p.insert_user)),
                (u(p), NS_DC["date"], Literal(p.insert_date)),

                }
                
    def _expected_triples_job(self):
        u, j = get_uri, self.job
        return {(u(j), PREDICATES["id"], Literal(j.id)),
                (u(j), PREDICATES["name"], Literal(j.name)),
                (u(j), NS_DC["creator"], u(j.insertuser)),
                (u(j), NS_DC["date"], Literal(j.insertdate)),
                (u(j), NS_AMCAT["articleschema"], u(self.schema)),
                (u(j), NS_AMCAT["project"], u(self.project)),
                (u(j), NS_AMCAT["coder"], u(j.coder)),
                (u(j), NS_DC["subject"], u(self.articleset)),
                }
    
    def _expected_triples_article(self):
        u, a = get_uri, self.article
        return {
            (u(a), NS_DC["identifier"], Literal(a.id)),
            (u(a), NS_DC["date"], Literal(u'2012-01-01T00:00:00', datatype=NS_XMLS['dateTime'])),
            (u(a), NS_DC["title"], Literal(self.article_hl)),
            (u(a), NS_DC["publisher"], u(a.medium)),
            (u(a), NS_AMCAT["project"], u(self.project)),
            (u(a), NS_AMCAT["text"], Literal(self.article_text)),
            }

    def _expected_triples_articleset(self):
        u, a, aset = get_uri, self.article, self.articleset
        return {
            (u(aset), NS_RDF["li"], u(a)),
            (u(aset), PREDICATES["id"], Literal(aset.id)),
            (u(aset), PREDICATES["name"], Literal(aset.name)),
            (u(aset), NS_AMCAT["project"], u(self.project)),
            }

    def test_triples_articleset(self):
        """Do we get the right triples from a article set?"""
        self.assertEqual(set(get_triples_articleset(self.articleset)),
                         self._expected_triples_articleset())
        
    
            
    def test_triples_project(self):
        """Do we get the right triples from a project?"""
        self.assertEqual(set(get_triples(self.project)),
                         self._expected_triples_project())


    def test_triples_article(self):
        """Do we get the right triples from an article?"""
        self.assertEqual(set(get_triples(self.article)),
                         self._expected_triples_article())
        

    def test_triples_codebooks(self):
        """Do we get the right triples from codebooks?"""
        cb_triples = self._expected_triples_codebook()

        self.assertEqual(set(get_triples_codebooks({self.codebook})), cb_triples)

        sub_triples = self._expected_triples_sub_codebook()
        
        self.assertEqual(set(get_triples_codebooks({self.codebook, self.sub_codebook})),
                         cb_triples | sub_triples)
        

    def test_triples_schema(self):
        self.assertEqual(set(get_triples_schema(self.schema)),
                         self._expected_triples_schema())
        
    def test_triples_coding(self):
        """Do we get the right triples from coded articles?"""

        
        self.assertEqual(set(get_triples_coding(self.coding)), self._expected_triples_coding())


    def test_full_project(self):
        """
        Test a complex example of a filled project
        """
        triples = set(get_triples_project(self.project))

        expected = (self._expected_triples_schema() 
                    |self._expected_triples_coding() 
                    |self._expected_triples_codebook() 
                    |self._expected_triples_sub_codebook()
                    |self._expected_triples_job()
                    |self._expected_triples_project()
                    |self._expected_triples_article()
                    |self._expected_triples_articleset()
                    )
        
        self.assertEqual(triples, expected)

        open("/tmp/test_project.rdf.xml", "w").write( serialize(triples, format="xml"))
        open("/tmp/test_project.rdf.nt", "w").write( serialize(triples, format="nt"))
        open("/tmp/test_project.rdf.n3", "w").write( serialize(triples, format="n3"))
        from amcat.scripts.actions.serialize_project import serialize_project_to_zipfile
        serialize_project_to_zipfile(self.project, open("/tmp/test_project.zip", "w"))
        

    def test_project_duplicates(self):
        triples = list(get_triples_project(self.project))
        self.assertEqual(len(triples), len(set(triples)), "Duplicate triples!")
        
        amcattest.create_test_set(project=self.project).add(self.article)

        triples = list(get_triples_project(self.project))
        self.assertEqual(len(triples), len(set(triples)), "Duplicate triples!")

        

    def test_get_triples_nqueries(self):
        """Does getting triples work with a single query?"""
        from amcat.models import Article
        a = amcattest.create_test_article()
        with self.checkMaxQueries(1):
            a = Article.objects.get(pk=a.id)
            triples = set(get_triples(a))
            # just assert something silly to make sure we have data...
            self.assertTrue(len(triples) > 5) 


    
