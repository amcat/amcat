import amcattest, articlecomparator, article

class ArticleComparatorTest(amcattest.AmcatTestCase):
    def testNGram(self):
        comp = articlecomparator.NGramComparator(n=3)
        for a1, a2, expectedresult in (
            (353570, 353571, 0.0),
            (353570, 353570, 1.0),
            ):
            self.assertEqual(comp.compareArticles(a1, a2), expectedresult)

if __name__ == '__main__':
    amcattest.main()
