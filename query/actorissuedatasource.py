import datasource 
import article
import ont2
import toolkit
import categorise
import lucenelib
import dbtoolkit
from ontologydatasource import *

class ActorIssueDataSource(OntologyDataSource):
    def __init__(self, dm, db, index):
        article = datasource.Field(self, dm.getConcept("article") )
        issue = SetOntologyField(self, dm.getConcept("issue"), 309, 307, 1)
        actor = SetOntologyField(self,dm.getConcept("actor"), 308, 307, 1)
        issuearticle = OntArtField(self, dm.getConcept("issuearticle"), issue)
        coocissue = datasource.Field(self, dm.getConcept("coocissue"))
        issuecooc = datasource.Field(self, dm.getConcept("issuecooc"))

        mappings = [
            ObjectArticleMapping(issue, article, db),
            ObjectArticleMapping(actor, article, db),
            ArticleOntArtMapping(article, issuearticle),
            OntArtObjectMapping(issuearticle, coocissue),
            OntArtCoocMapping(issuearticle, issuecooc),
            ]
        OntologyDataSource.__init__(self, dm, db, index, mappings)

if __name__ == '__main__':
    import dbtoolkit, ont2
    db = dbtoolkit.amcatDB()
    ont = ont2.fromDB(db)

    class Y(object): pass
    x = Y()
    x.ont = ont

    f = HierarchyOntologyField(x, None, 16104, 10002, depth=2)
    for o in f.getObjects():
        print o, f.getQuery(o)
