import datasource
from amcatmetadatasource import ConceptMapper, MappedField
import collections
import toolkit
import cachable

PARTIES = [514,2045,2653,952,1019,1052,1098,1142,1156,1373,1545,1857,1906,1934]
IDEAL = 1625
REALITY = 2547
IDEAL_ATYPE = 2

class NETDataSource(datasource.DataSource):
    def __init__(self, dm, db, projectid):
        import project, article
        artfield = MappedField(self, dm.getConcept("article"), ConceptMapper(db, article.Article))
        subject = datasource.Field(self,dm.getConcept("subject"))
        object = datasource.Field(self,dm.getConcept("object"))

        arrow = NETArrowField(self, dm.getConcept("arrow"))
        quality = datasource.Field(self, dm.getConcept("quality"))

        proj = project.Project(db, projectid)
        
        mappings = [
            ArticleArrowMapping(artfield, arrow, proj),
            ArrowObjectMapping(arrow, subject, True),
            ArrowObjectMapping(arrow, object, False),
            ArrowQualityMapping(arrow, quality),
            ]
        datasource.DataSource.__init__(self,  mappings)

        self.db = db
    
    def deserialize(self, concept, id):
        import ont
        if concept.label in ("subject","object"):
            return ont.Object(self.db, id)
    
class NETArrowField(datasource.Field):
    def __init__(self, ds, concept):
        datasource.Field.__init__(self, ds, concept)

class Arrow(object):
    def __init__(self, article, subject, quality, object):
        self.article = article
        self.subject = subject
        self.quality = quality
        self.object = object
        
class ArrowObjectMapping(datasource.Mapping):
    def __init__(self,a,b,subject=True):
        datasource.Mapping.__init__(self, a, b, 100.0, 99999999)
        self.subject=subject
    def map(self, value, reverse, memo=None):
        if reverse:
            raise Exception("Not supported")
        return [value.subject] if self.subject else [value.object]

class ArrowQualityMapping(datasource.Mapping):
    def __init__(self,a,b):
        datasource.Mapping.__init__(self, a, b, 100.0, 99999999)
    def map(self, value, reverse, memo=None):
        if reverse:
            raise Exception("Not supported")
        return [value.quality]


UGLY_SQL = """select articleid, source, subject, arrowtype, quality, object
from net_arrows r 
inner join codingjobs_articles ca on r.codingjob_articleid = ca.codingjob_articleid
inner join codingjobs j on ca.codingjobid = j.codingjobid
where projectid=%i AND %s"""
    
class ArticleArrowMapping(datasource.Mapping):
    def __init__(self, a,b,project):
        datasource.Mapping.__init__(self, a, b, 100.0, 999999999)
        self.db = project.db
        self.project = project
        self.categories = None

    def getObject(self, x):
        import ont
        if self.categories is None:
            self.categories = {}
            for pol, party in self.db.doQuery("select distinct objectid, office_objectid from o_politicians_functions where functionid=0 and todate is null"):
                self.categories[pol] = ont.Object(self.db, party)
            iderea = {100 : ont.Object(self.db, 2547), 200 : ont.Object(self.db, 1625)}
            for cls, obj in self.db.doQuery("select classid, childid from o_hierarchy where classid in (%s)" % ",".join(map(str, iderea.keys()))):
                self.categories[obj] = iderea[cls]

        return self.categories.get(x)
    
    def map(self, value, reverse, memo=None):
        if reverse:
            raise Exception("Not supported")
        return memo[value]

    def startMapping(self, values, reverse=False):
        if reverse:return
        memo = collections.defaultdict(set)
        sql = UGLY_SQL % (self.project.id, toolkit.intselectionTempTable(self.db, "articleid", values))
        for art, source, subject,  atype, quality, object in self.db.doQuery(sql):
            # oordeelextrapolatie
            if source and atype == IDEAL_ATYPE:
                subject, object = source, subject
            #print subject, object
            subject = self.getObject(subject)
            object = self.getObject(object)
            quality = quality
            if subject and object:
                memo[art].add(Arrow(art, subject, quality, object))
        return memo
            
        
        
        
