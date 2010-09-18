import unittest, sentence, dbtoolkit

SENTENCES = { # sid, sent, parnr, sentnr, preprocessed_words?
    34616637 : ("nog een nieuwgefetste zin", 1, 20)
    }

LEMMATA = { # sid, sent, parnr, sentnr, preprocessed_words?
    34616637 : "nog een nieuwgefetste zin",
    }

PARSES_WORDS = {
    34616637 : [2]
    }
   
PARSES_TRIPLES = {
    34616637 : [2]
    }

class TestSentences(unittest.TestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(profile=True, use_app=True)
    
    def test_analysedsentence_words(self):
        for sid, (sent, parnr, sentnr) in SENTENCES.items():
            for analysisid in PARSES_WORDS.get(sid, []):
                a = sentence.AnalysedSentence(self.db, (sid, analysisid))
                words = a.words
                words2 = sent.split()
                self.assertEqual(len(words), len(words2))
                for i, w in enumerate(words2):
                    word = a.getWord(i)
                    self.assertEqual(str(word.word), w)
                    self.assertEqual(word.position, i)

    def test_analysedsentence_triples(self):
        for sid, anids in PARSES_TRIPLES.items():
            for anid in anids:
                a = sentence.AnalysedSentence(self.db, sid, anid)
                nodes = set()
                for p, rel, c in a.triples: nodes |= set([p,c])
                self.assertEqual(nodes, set(a.getNodes()))
                self.assertEqual(nodes, set(a.words))
                
                    

    def test_sentence(self):
        for sid, (sent, parnr, sentnr) in SENTENCES.items():
            s = sentence.Sentence(self.db, sid)
            self.assertEqual(s.parnr, parnr)
            self.assertEqual(s.sentnr, sentnr)
            self.assertEqual(str(s), sent)
            self.assertEqual(set(PARSES_WORDS.get(sid, [])),
                             set(a.analysisid for a in s.analysedSentences))

    def test_aaa_cacheWords(self): # aaa to determine sort order
        sentences = [sentence.Sentence(self.db, sid) for sid in SENTENCES]
        sentence.cacheWords(sentences, lemmata=True, sentence=True)
        self.db.conn, _conn = None, self.db.conn
        try:
            for sid, (sent, parnr, sentnr) in SENTENCES.items():
                s = sentence.Sentence(self.db, sid)
                self.assertEqual(str(s), sent)
                for a in s.analysedSentences:
                    self.assertEqual(" ".join(str(w.word.lemma) for w in a.words), LEMMATA[sid])
        finally:
            self.db.conn = _conn
        
    def tearDown(self):
        #self.db.printProfile()
        pass
            
if __name__ == '__main__':
    unittest.main()
