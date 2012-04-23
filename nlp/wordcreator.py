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
Toolkit for creating Words, Lemmata, POS, and Relations more efficiently
"""
import collections
from amcat.models import Lemma, Pos, AnalysisSentence
from amcat.models.token import Token
from amcat.models.word import Word
from amcat.tools import toolkit

def create_objects(cls, values, key_attrs):
    """
    Create and/or retrieve multiple instances of cls (Model) objects from a sequence of objects
    @param cls: The model class
    @param values: A sequence of objects with attrs values attributes (e.g. TokenValues)
    @param key_attrs: the attributes forming the 'key' of the objects (e.g. lemma+pos for lemmata)
                      Note: if an attribute contains '_id' it is removed from the retrieval query
    @return: a sequence of the created/retrieved objects
    """
    def key(obj):
        """create a tuple (obj.a, obj.b) to use as dict key (assuming key_attrs='a','b')"""
        return tuple(getattr(obj, attr) for attr in key_attrs)
    # first create a cache containing the objects with any of the possible key values
    query = cls.objects.all()
    for attr in key_attrs:
        query = query.filter(**{"{}__in".format(attr.replace("_id","")) : set(getattr(v, attr) for v in values)})

    cache = dict((key(obj), obj) for obj in query)

    # then select objects from the cache with the right key values, or create as needed
    for v in values:
        try:
            yield cache[key(v)]
        except KeyError:
            l = cls.objects.create(**dict((attr, getattr(v, attr)) for attr in key_attrs))
            cache[key(l)] = l
            yield l

def create_lemmata(tokenvalues):
    """Create a dict of {lemma_string, pos : Lemma} from the TokenValue objects"""
    return dict(((lemma.lemma, lemma.pos), lemma) for lemma in
                 create_objects(Lemma, tokenvalues, ["lemma", "pos"]))

_WordValues = collections.namedtuple("WordValues", ["lemma_id", "word"])
@toolkit.wrapped(dict)
def create_words(tokenvalues):
    """Create a dict of  {lemma_string, pos, word_wtring: Lemma} from the TokenValue objects,
    creating lemmata as needed"""
    lemmata = create_lemmata(tokenvalues)
    wordvalues = [_WordValues(word=v.word, lemma_id=lemmata[v.lemma, v.pos].id) for v in tokenvalues]
    words = create_objects(Word, wordvalues, ["lemma_id", "word"])
    for tv, word in zip(tokenvalues, words):
        yield (tv.lemma, tv.pos, tv.word), word

def create_pos(tokenvalues):
    """Create a dict of {major, minor, pos_char : Pos} from the given tokenvalues"""
    return dict(((p.major, p.minor, p.pos), p) for p in create_objects(Pos, tokenvalues, ["major","minor","pos"]))

@toolkit.wrapped(list)
def create_tokens(tokenvalues):
    """Create a list of new Token objects from a language and tokenvalues sequence"""
    words = create_words(tokenvalues)
    poss = create_pos(tokenvalues)
    sentences = dict((s.id, s) for s in
        AnalysisSentence.objects.filter(pk__in=set(v.analysis_sentence for v in tokenvalues)))
    for v in tokenvalues:
        word = words[v.lemma, v.pos, v.word]
        pos = poss[v.major, v.minor, v.pos]
        yield Token.objects.create(sentence=sentences[v.analysis_sentence], position=v.position, word=word, pos=pos)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestWordCreator(amcattest.PolicyTestCase):
    def test_create_lemmata(self):
        from amcat.models.token import TokenValues
        lang = amcattest.get_test_language()
        l1 = Lemma.objects.create(lemma="a", pos="b")
        tokens = [TokenValues(None, None, None, lemma=l, pos="b", major=None, minor=None)
                  for l in "a"*10]
        tokens += [TokenValues(None, None, None, lemma=l, pos="c", major=None, minor=None)
                  for l in "ab"*5]
        with self.checkMaxQueries(3): # 1 to cache, 2 to create with different poss
            lemmata = create_lemmata(tokens)
        # are existing lemmata 'recycled'?
        self.assertEqual(lemmata["a","b"].id, l1.id)
        # did we get the correct lemmata?
        self.assertEqual(set(lemmata.keys()), set([("a","b"), ("a","c"), ("b","c")]))
        for (lemmastr, pos), lemma in lemmata.items():
            self.assertEqual(lemma.lemma, lemmastr)


    def test_create_words(self):
        from amcat.models.token import TokenValues
        lang = amcattest.get_test_language()
        tokens = []
        l1 = Lemma.objects.create(lemma="a", pos="b")
        w1 = Word.objects.create(lemma=l1, word="b")
        for lemma in "ab":
            for word in "bbcc":
                tokens.append(TokenValues(None, None, word=word, lemma=lemma, pos="b", major=None, minor=None))
        with self.checkMaxQueries(8): # 2 to cache lemmata+words, 1 to create lemmata, 5 to create words
            words = create_words(tokens)

        self.assertEqual(set(words.keys()), set([("a","b", "b"), ("a","b","c"), ("b","b", "b"), ("b","b","c")]))
        for (lemmastr, pos, wordstr), word in words.items():
            self.assertEqual(word.word, wordstr)
            self.assertEqual(word.lemma.lemma, lemmastr)

        self.assertEqual(words["a", "b", "b"].id, w1.id)
        self.assertEqual(words["a", "b", "c"].lemma_id, l1.id)


    def test_create_tokens(self):
        from amcat.models.token import TokenValues
        s = amcattest.create_test_analysis_sentence()
        tokens = [TokenValues(s.id, 2, word="w", lemma="l", pos="p", major="major", minor="minor")]
        token, = create_tokens(tokens)
        self.assertEqual(token.word.lemma.lemma, "l")