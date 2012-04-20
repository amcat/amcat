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
Script to add tokens (and triples) from a json representation 
"""

import logging; log = logging.getLogger(__name__)

from django import forms

from amcat.scripts.script import Script
from amcat.forms.fields import JSONField

from amcat.models import Article, Analysis, Language, ArticleAnalysis, Token, Triple

from amcat.nlp import analysisscript

import json

class AddTokensForm(forms.Form):
    articleanalysis = forms.ModelChoiceField(queryset=ArticleAnalysis.objects.all())
    tokens = forms.CharField()
    triples = forms.CharField(required=False)

    def clean_tokens(self):
        tokens = self.cleaned_data["tokens"]
        try:
            return [analysisscript.Token(*fields) for fields in json.loads(tokens)]
        except ValueError as e:
            raise forms.ValidationError(e)

    def clean_triples(self):
        triples = self.cleaned_data["triples"]
        if not triples: return
        return [analysisscript.Triple(*fields) for fields in json.loads(triples)]
    
class AddTokens(Script):
    """Add a project to the database."""

    options_form = AddTokensForm
    output_type = None

    def run(self, _input=None):
        aa, tokens, triples = (self.options[x] for x in ['articleanalysis', 'tokens', 'triples'])
        aa.store_analysis(tokens, triples)
        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAddTokens(amcattest.PolicyTestCase):
    
    def test_store_tokens(self):
        s = amcattest.create_test_sentence()
        a = amcattest.create_test_analysis()
        aa = ArticleAnalysis.objects.create(article=s.article, analysis=a)
        t1 = amcattest.create_analysis_token(sentence_id=s.id)
        AddTokens(articleanalysis=aa.id, tokens=json.dumps([t1])).run()
        aa = ArticleAnalysis.objects.get(pk=aa.id)
        self.assertEqual(aa.done,  True)
        token, = list(Token.objects.filter(sentence=s, analysis=a))
        self.assertEqual(token.word.word, t1.word)
        self.assertRaises(aa.store_analysis, tokens=[t1])
        with self.assertRaises(Exception):
            AddTokens(articleanalysis=aa.id, tokens=json.dumps(tokens)).run()

    def test_store_triples(self):
        from amcat.nlp import analysisscript
        s = amcattest.create_test_sentence()
        a = amcattest.create_test_analysis()
        aa = ArticleAnalysis.objects.create(article=s.article, analysis=a)
        t1 = amcattest.create_analysis_token(sentence_id=s.id, position=1)
        t2 = amcattest.create_analysis_token(sentence_id=s.id, word="x")
        tr = analysisscript.Triple(s.id, parent=t1.position, child=t2.position, relation='su')
        AddTokens(articleanalysis=aa.id, tokens=json.dumps([t1, t2]),
                  triples=json.dumps([tr])).run()
        aa = ArticleAnalysis.objects.get(pk=aa.id)
        triple, = list(Triple.objects.filter(analysis=a, parent__sentence=s))
        self.assertEqual(triple.parent.word.word, t1.word)
        self.assertEqual(triple.child.word.lemma.lemma, t2.lemma)
