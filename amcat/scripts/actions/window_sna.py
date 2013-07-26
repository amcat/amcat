#!/usr/bin/python
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
Script for computing object-object networks based on object co-occurrence in
scrolling windows of tokens.
"""
import logging
import itertools
import collections

from django import forms

from amcat.models import ArticleSet, Plugin, Codebook, Language, AnalysedArticle
from amcat.scripts.script import Script

log = logging.getLogger(__name__)

class WindowedSNAScript(Script):
    """"
    Create an object-object network based on a scrolling window of tokens

    General approach is to first create a "codestream" where codes are recognized
    in the stream of input tokens (e.g. the words in the articles). Then, the
    windower outputs code-code edges based on window size etc.
    """

    
    class options_form(forms.Form):
        articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
        plugin = forms.ModelChoiceField(queryset=Plugin.objects.all())
        codebook = forms.ModelChoiceField(queryset=Codebook.objects.all())
        lexicon_language = forms.ModelChoiceField(queryset=Language.objects.all())
        window_size = forms.IntegerField()
        
    def run(self):
        tokenstream = self.get_tokenstream()
        classifier = self.get_classifier()
        codestream = self.get_codestream(tokenstream, classifier)
        windower = self.get_windower()
        return windower(codestream)

    def get_tokenstream(self):
        """
        Create the tokenstream based on the articleset and plugin
        @return: a sequence of Token objects
        """
        articles = AnalysedArticle.objects.filter(article__articlesets_set=self.options["articleset"],
                                                  plugin=self.options["plugin"])
        for article in articles:
            for sentence in article.sentences.all():
                for token in sentence.tokens.all():
                    yield token
            
    def get_classifier(self):
        """
        Get the token classifier based on the codebook and language
        @return: a method that maps a token to a sequence of codes
        """
        return TokenClassifier(self.options["codebook"], self.options["lexicon_language"]).get_codes

    def get_codestream(self, tokenstream, classifier):
        """
        Transform the tokenstream into a codestream using the classifier
        @param tokenstream: a sequence of Token
        @param classifier: a function of Token to sequence of Code
        @return: a sequence of (possibly empty) sets of Code
        """
        for token in tokenstream:
            yield set(classifier(token))

    def get_windower(self):
        """
        Get the windower <- better term?
        @return: a function that transforms a sequence of {Code,} sets to a sequence of Edge
        """
        return Windower(window_size = self.options["window_size"]).get_edges
            
Edge = collections.namedtuple("Edge", ["subject", "object", "weight"])
            
class Windower(object):
    def __init__(self, window_size=10):
        self.window_size = window_size

    def get_edges(self, codestream):
        """
        Extract the code-code edges from the codestream
        @param codes: a sequence of {Code, } sets
        @return: a sequence of Edge objects
        """
        stack = []
        for codes in codestream:
            stack.append(codes)
            stack = stack[-self.window_size:]
            log.debug("Added {codes}, stack now {stack}".format(**locals()))

            for edge in self.get_edges_from_stack(stack):
                yield edge

    def get_edges_from_stack(self, stack):
        for i, codes1 in enumerate(stack):
            if not codes1: continue
            for codes2 in stack[(i+1):]:
                if not codes2: continue

                log.debug(".. Getting codes from {codes1} : {codes2}".format(**locals()))
                for c1 in codes1:
                    for c2 in codes2:
                        log.debug(".... Edge: {c1}->{c2}".format(**locals()))
                        yield Edge(c1, c2, 1)
                        if c1 != c2:
                            yield Edge(c2, c1, 1)
        

class TokenClassifier(object):
    """Determine whether codes occur in given tokens"""
    
    def __init__(self, codebook, language):
        self.codebook = codebook
        self.language = language
        self.codebook.cache_labels(language)

    def get_labels(self):
        return ((c, c.get_label(self.language)) for c in self.codebook.get_codes())
        
    def get_codes(self, token):
        w = token.word.word
        for code, label in self.get_labels():
            if token.word.word == label:
                yield code

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestWindowedSNA(amcattest.PolicyTestCase):
    def _get_test_tokens(self, aa, words):
        s = amcattest.create_test_analysis_sentence(analysed_article=aa)
        if not words: words = "abcde"
        return [amcattest.create_test_token(sentence=s, position=i, word=amcattest.create_test_word(word=w))
                for (i,w) in enumerate(words)]

    def _get_test_codebook(self, lexicon_language, codes):
        """@param codes: a dict of label : lexical entry"""
        cb = amcattest.create_test_codebook()
        for label, lexical in codes.iteritems():
            c = amcattest.create_test_code(codebook=cb, label=label)
            c.add_label(lexicon_language, lexical)
        cb.cache_labels(1)
        return cb

    def _get_test_script(self, words=None, codes={}, window_size=5):
        aa = amcattest.create_test_analysed_article()
        tokens = self._get_test_tokens(aa, words)
        aset = amcattest.create_test_set(articles=[aa.article])
        lexicon_lang = Language.objects.get(pk=2)
        cb = self._get_test_codebook(lexicon_lang, codes)
        return WindowedSNAScript(articleset=aset.id, plugin=aa.plugin.id,
                                 codebook=cb.id, lexicon_language=lexicon_lang.id,
                                 window_size=window_size)
        
    
    def test_tokenstream(self):
        script = self._get_test_script(words="this is a test".split())
        tokenstream = list(script.get_tokenstream())
        self.assertEqual([t.word.word for t in tokenstream], ["this","is","a","test"])

    def test_classifier(self):
        lang = Language.objects.get(pk=2)
        codes = dict(det="de het een", test="test*")
        cb = self._get_test_codebook(lang, codes)
        c = TokenClassifier(cb, lang)
        self.assertEqual({code.label: label for (code, label) in c.get_labels()}, codes)

    def test_codestream(self):
        words = "dit is een test".split()
        codes = dict(det="dit", dit="dit", test="test")
        script = self._get_test_script(words, codes)
        
        codes = list(script.get_codestream(script.get_tokenstream(), script.get_classifier()))

        codes = [{c.get_label(1) for c in element} for element in codes]
        self.assertEqual(codes, [{"dit", "det"}, set(), set(), {"test"}])

    def test_windower(self):
        codes = ["ab", "", "a", "c"]
        w = Windower(window_size=2)
        edges = sorted("{e.subject}-{e.object}".format(**locals()) for e in w.get_edges(codes))
        self.assertEqual(edges, sorted(["a-c", "c-a"]))

        w = Windower(window_size=3)
        edges = sorted("{e.subject}-{e.object}".format(**locals()) for e in w.get_edges(codes))
        self.assertEqual(edges, sorted(["a-a", "b-a", "a-b", "a-c", "c-a"]))

    def test_script(self):
        #from amcat.tools import amcatlogging
        #amcatlogging.setup()
        #amcatlogging.debug_module()
        words = "dit is een mooie test".split()
        codes = dict(d1="dit", d2="dit", e="een", t="test")
        script = self._get_test_script(words, codes, window_size=3)
        edges = sorted("{a}-{b}".format(a=e.subject.get_label(1), b=e.object.get_label(1)) for e in script.run())
        self.assertEqual(edges, sorted(["d1-e", "d2-e", "e-d1", "e-d2", "e-t", "t-e"]))
