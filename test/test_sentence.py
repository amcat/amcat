from amcat.test import amcattest
from amcat.model import sentence

SENTENCES = { # sid, sent, parnr, sentnr, preprocessed_words?
    63985791 : ("Peace activists targeted by FBI call Minneapolis home raids harassment", 1,1),
    }

class TestSentences(amcattest.AmcatTestCase):
    def test_cacheWords(self): 
        sentences = [sentence.Sentence(self.db, sid) for sid in SENTENCES]
        for s in sentences:
            s.uncache()
        sentence.cacheWords(sentences, sentence=True)
        with self.db.disabled():
            for sid, (sent, parnr, sentnr) in SENTENCES.items():
                s = sentence.Sentence(self.db, sid)
                self.assertEqual(str(s), sent)
class Stop:
    def test_sentence(self):
        for sid, (sent, parnr, sentnr) in SENTENCES.items():
            s = sentence.Sentence(self.db, sid)
            self.assertEqual(s.parnr, parnr)
            self.assertEqual(s.sentnr, sentnr)
            self.assertEqual(str(s), sent)

                
if __name__ == '__main__':
    amcattest.main()
