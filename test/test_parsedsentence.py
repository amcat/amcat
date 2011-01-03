import amcattest, parsedsentence

from test_sentence import SENTENCES

LEMMATA = { # sid, sent, parnr, sentnr, preprocessed_words?
    63985791 : "peace activist target by fbi call minneapolis home raid harassment",
    }

PARSES_WORDS = {
    63985791 : [4]
    }
   
PARSES_TRIPLES = {
    63985791 : [4]
    }


class TestSentences(amcattest.AmcatTestCase):
    def test_analysedsentence_words(self):
        for sid, (sent, parnr, sentnr) in SENTENCES.items():
            for analysisid in PARSES_WORDS.get(sid, []):
                a = parsedsentence.ParsedSentence(self.db, (sid, analysisid))
                words = list(a.words)
                words2 = sent.split()
                self.assertEqual(len(words), len(words2))
                for i, w in enumerate(words2):
                    word = a.getWord(i)
                    self.assertEqual(str(word.word).lower(), w.lower())
                    self.assertEqual(word.position, i)
                self.assertEqual(" ".join(str(w.word.lemma) for w in a.words), LEMMATA[sid])
                    
    def test_analysedsentence_triples(self):
        for sid, anids in PARSES_TRIPLES.items():
            for anid in anids:
                a = parsedsentence.ParsedSentence(self.db, sid, anid)
                nodes = set()
                for triple in a.triples:
                    nodes |= set([triple.parent,triple.child])

                
                self.assertEqual(nodes, set(a.getNodes()))
                self.assertEqual(nodes, set(a.words))
                
            
if __name__ == '__main__':
    amcattest.main()
