from amcat.test import amcattest
from amcat.model import word

class TestWord(amcattest.AmcatTestCase):    

    def testWord(self):
        for (wordid, wordstringid, wordstr, lemmaid, lemmastringid, pos, lemmastr) in [
            (7, 50681, 'aagtappel', 7, 50681, 'N', 'aagtappel'),
            (8, 539087, 'aagtappelen', 7, 50681, 'N', 'aagtappel'),
            ]:
            w = word.Word(self.db, wordid)
            l = word.Lemma(self.db, lemmaid)
            self.assertEqual(str(w), wordstr)
            self.assertEqual(w.label, wordstr)
            self.assertEqual(str(w.word), wordstr)
            self.assertEqual(w.word.id, wordstringid)

            self.assertEqual(w.lemma, l)
            for x in (w.lemma, l): 
                self.assertEqual(str(x), lemmastr)
                self.assertEqual(str(x.lemma), lemmastr)
                self.assertEqual(x.label, lemmastr)
                self.assertEqual(x.id, lemmaid)
                self.assertEqual(x.pos, pos)
                self.assertEqual(x.lemma.id, lemmastringid)


    def skip_testSentiment(self):
        l = word.SentimentLexicon(self.db, 1)
        d = l.lemmaidDict()
        
        for (lemmaid, lexiconid, sentiment, intensity) in [
            (91, 1, 100, 0),
            ]:

            l = word.Lemma(self.db, lemmaid)
            sl = l.sentimentLemma(lexiconid)
            self.assertEqual(sl.sentiment, sentiment)
            self.assertEqual(sl.intensity, intensity)
            self.assertEqual(sl.lexicon.id, lexiconid)
            self.assertEqual(sl.lemma.id, lemmaid)

            self.assertEqual(d.get(lemmaid), sl)
                
if __name__ == '__main__':
    amcattest.main()
                
                
            
            
        
