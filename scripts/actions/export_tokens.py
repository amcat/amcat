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
Script to export tokens (and triples) to a json representation 
"""

from django.db import connection
from amcat.tools.djangotoolkit import list_queries
from amcat.models.token import TokenValues, TripleValues
from amcat.models import Token, Triple, Sentence, ArticleSet
import json
import sys


from django import forms

from amcat.scripts.script import Script

class ExportTokensForm(forms.Form):
    articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
    
class ExportTokens(Script):
    """Export tokens to json."""

    options_form = ExportTokensForm
    output_type = None

    def run(self, _input=None):
        
        articles = self.options["articleset"].articles.only("uuid")

        print "[" # manually output json so we don't need to keep all in memory
        
        def sent_tuple(article, analysissentence):
            return (analysissentence.sentence.parnr, analysissentence.sentence.sentnr)

        for i, a in enumerate(articles):
            if i: print ","

            print >>sys.stderr, "{i} / {n}: {a.id} / {a.uuid}".format(n=len(articles), **locals())
            sentences = list(a.sentences.all())
            sentencevalues = [(s.parnr, s.sentnr, s.sentence) for s in sentences]

            tokens = list(Token.objects.filter(sentence__sentence__in=sentences)
                          .select_related("sentence__sentence", "word", "word__lemma", "pos"))

            sent_tuples = {t : sent_tuple(a, t.sentence) for t in tokens}
            
            tokenvalues = [TokenValues(sent_tuples[t],
                                        t.position, t.word.word, t.word.lemma.lemma,
                                        t.pos.pos, t.pos.major, t.pos.minor, None)
                            for t in tokens]

            triples = list(Triple.objects.filter(child__in=tokens)
                           .select_related("child", "parent", "relation"))

            triplevalues = [TripleValues(sent_tuples[t.child],
                                         t.child.position, t.parent.position,t.relation.label)
                            for t in triples]
            data = dict(article=a.uuid, sentences=sentencevalues, tokens=tokenvalues, triples=triplevalues)

            json.dump(data, sys.stdout)
            sys.stdout.flush()
            

        print "]"

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
