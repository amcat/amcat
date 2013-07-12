###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
Simple regex-based sentence boundary detection
"""

import re, collections
from amcat.tools import toolkit

abbrevs = ["ir","mr","dr","dhr","ing","drs","mrs","sen","sens","gov","st",
           "jr","rev","vs","gen","adm","sr","lt","sept"]
months = ["Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

from amcat.models.sentence import Sentence

def get_split_regex():
    global _split_regex
    try:
        return _split_regex
    except NameError:
        lenmap = collections.defaultdict(list)
        for a in abbrevs+months:
            lenmap[len(a)].append(a)
            lenmap[len(a)].append(a.title())
        expr = r"(?<!\b[A-Za-z])"
        for x in lenmap.values():
            expr += r"(?<!\b(?:%s))" % "|".join(x)
            #expr += r"(?<Nov(?=. \d))"
        expr += r"[\.?!](?!\.\.)(?<!\.\.)(?!\w|,)(?!\s[a-z])|\n\n"
        expr += r"|(?<=%s)\. (?=[^\d])" % "|".join(months)
        _split_regex = re.compile(expr)
        return _split_regex

def get_or_create_sentences(article):
    """
    Split the given article object into sentences and save the sentences models
    to the database. Returns a list of the resulting Sentence objects.

    This function (as opposed to create_sentences) does not error when an article
    is already split.
    """
    if not article.sentences.exists():
        create_sentences(article)
    return article.sentences.all()

def _create_sentences(article):
    pars = [article.headline]
    if article.byline: pars += [article.byline]
    pars += re.split(r"\n\s*\n[\s\n]*", article.text.strip())
    for parnr, par in enumerate(pars):
        for sentnr, sent in enumerate(split(par)):
            yield Sentence(parnr=parnr+1, sentnr=sentnr+1,
                            article=article, sentence=sent)

def create_sentences(article):
    """
    Split the given article object into sentences and save the sentences models
    to the database. Returns a list of the resulting Sentence objects.

    If you can, cache properties headline, byline and text.
    """
    sents = tuple(_create_sentences(article))
    Sentence.objects.bulk_create(sents)
    return sents


def split(text):
    """
    Split the text into sentences and yield the sentence strings
    """
    text = re.sub("\n\n+", "\n\n", text)
    text = text.replace(".'", "'.")

    return (re.sub('\s+', ' ', sent.strip())
            for sent in get_split_regex().split(text)
            if sent.strip())


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestSBD(amcattest.PolicyTestCase):
    def test_split(self):
        """Does splitting a text work correctly?"""
        for text, sentences in [
            ("Wat een zin! En nu s.v.p. nog een zin.",
             ["Wat een zin", "En nu s.v.p. nog een zin"]),
            ]:
            result = list(split(text))
            self.assertEqual(result, sentences)

    def test_create_sentences(self):
        hl = "This is the headline"
        text="A sentence.\n\nAnother sentence. And yet a third"
        a = amcattest.create_test_article(headline=hl, text=text)
        create_sentences(a)
        sents = Sentence.objects.filter(article=a.id)
        sents = set((s.parnr, s.sentnr, s.sentence) for s in sents)
        self.assertEqual(sents, {(1,1,hl),
                                 (2,1,"A sentence"),
                                 (3,1,"Another sentence"),
                                 (3,2,"And yet a third")})

                                          
        
