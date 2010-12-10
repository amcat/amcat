import amcattest, word

class TestWord(amcattest.AmcatTestCase):    

    def testWord(self):
        for (wordid, wordstringid, word, lemmaid, lemmastringid, pos, lemma) in [
            (7, 50681, 'aagtappel', 7, 50681, 'N', 'aagtappel'),
            (8, 539087, 'aagtappelen', 7, 50681, 'N', 'aagtappel'),
            ]:
            w = word.Word(self.db, wordid)
            l = word.Lemma(self.db, lemmaid)
            self.assertEqual(str(w), word)
            self.assertEqual(w.label, word)
            self.assertEqual(str(w.word), word)
            self.assertEqual(w.word.id, wordstringid)

            self.assertEqual(w.lemma, l)
            for x in (w.lemma, l): 
                self.assertEqual(str(x), lemma)
                self.assertEqual(str(x.lemma), lemma)
                self.assertEqual(x.label, lemma)
                self.assertEqual(x.id, lemmaid)
                self.assertEqual(x.pos, pos)
                self.assertEqual(x.lemma.id, lemmastringid)
                
                
                
            
            
        
