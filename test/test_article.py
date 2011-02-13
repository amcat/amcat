from amcat.test import amcattest
from amcat.model import article
from amcat.tools import toolkit

class TestArticle(amcattest.AmcatTestCase):


    def testProperties(self):
        for (aid, projectid, sourceid, date, section, pagenr, headline, length, text) in [
            (57356176, 428, 707, '2006-11-14', None, 1, u"Van Cau a bien favoris\xe9 son ami", 151, u'P.4 affaire immo-congo : il y a eu injonction pour'),
	    ]:

            a = article.Article(self.db, aid)
            self.assertEqual(a.id, aid)
            self.assertEqual(a.source.id, sourceid)
            self.assertEqual(a.project.id, projectid)
            self.assertEqual(a.section, section)
	    self.assertEqual(a.text[:50], text)
            self.assertEqual(a.headline, headline)
            self.assertEqual(toolkit.writeDate(a.date), date)
            self.assertEqual(a.length, length)
    
        
if __name__ == '__main__':
    amcattest.main()
