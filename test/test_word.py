import amcattest, word

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

if __name__ == '__main__':
    amcattest.main()
                
                
            
            
        
