import amcattest, articlecomparator, article

class ArticleComparatorTest(amcattest.AmcatTestCase):
    def testNGram(self):
        comp = articlecomparator.NGramComparator(n=3)
        for a1, a2, expectedresult in (
            (45321989, 45322229, 0.0),
            (45321989, 45321989, 1.0),
            ):
            self.assertEqual(comp.compareArticles(a1, a2), expectedresult)

    def testCompareAll(self):
        comp = articlecomparator.NGramComparator(n=3)
        arts1, arts2 = [45321989, 4532222], [4532222,45321989]
        expectedresult = set([(45321989, 45321989, 1.0), (45321989, 4532222, 0.0), (4532222,4532222, 1.0), (4532222,45321989, 0.0)])
        self.assertEqual(set(comp.compareAll(arts1, arts2)), expectedresult)

    def testfindBestMatch(self):
        comp = articlecomparator.NGramComparator(n=3)
        art, arts = 45321989, [45321989, 45322229]
        expectedresult = (45321989, 1.0)
        self.assertEqual((comp.findBestMatch(art, arts)), expectedresult)

if __name__ == '__main__':
    amcattest.main()
