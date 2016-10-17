from amcat.models import Sentence
from amcat.tools import amcattest
from amcat.tools.sbd import split, create_sentences


class TestSBD(amcattest.AmCATTestCase):
    def test_split(self):
        """Does splitting a text work correctly?"""
        for text, sentences in [
            ("Wat een zin! En nu s.v.p. nog een zin.",
             ["Wat een zin", "En nu s.v.p. nog een zin"]),
        ]:
            result = list(split(text))
            self.assertEqual(result, sentences)

    def test_create_sentences(self):
        hl = "This is the title"
        text = "A sentence.\n\nAnother sentence. And yet a third"
        a = amcattest.create_test_article(title=hl, text=text)
        create_sentences(a)
        sents = Sentence.objects.filter(article=a.id)
        sents = set((s.parnr, s.sentnr, s.sentence) for s in sents)
        self.assertEqual(sents, {(1, 1, hl),
                                 (2, 1, "A sentence"),
                                 (3, 1, "Another sentence"),
                                 (3, 2, "And yet a third")})