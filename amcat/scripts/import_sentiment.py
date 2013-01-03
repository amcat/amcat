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
Import a sentiment lexicon
"""

from django import forms

from amcat.models.language import Language
from amcat.models.word import Lemma
from amcat.models.sentiment import SentimentLexicon, SentimentLemma
from amcat.scripts.script import Script
from amcat.tools.djangotoolkit import get_or_create

import csv

class LexiconForm(forms.Form):
    """Form for scrapers"""
    language = forms.ModelChoiceField(queryset=Language.objects.all())
    lexicon = forms.CharField()
    noheader = forms.BooleanField(initial=False, required=False)
    delimiter = forms.CharField(initial=",")

pos_map = {'ADV' : 'B',
	   'ADJECTIEF' : 'A',
	   'BIJWOORD' : 'B',
	   'NAAM' : None,
	   'NOUN' : 'N',
	   'VERB' : 'V'}

sent_map = dict(negative=-1, positive=1, positief=1, negatief=-1)
intense_map = dict(int=3)

def dict_slice(dict, keys):
    return {k : dict[k] for k in keys}
    
class ImportLexiconScript(Script):
    options_form = LexiconForm
    input_type = file

    def run(self, input):
	language = self.options['language']
	lexicon_name = self.options['lexicon']
	delimiter = str(self.options['delimiter'])
	lex = get_or_create(SentimentLexicon, language=language, label=lexicon_name)

	if not self.options['noheader']:
	    input.readline()
	
	for lemma, pos, value in csv.reader(input, delimiter=delimiter):
	    pos = pos_map.get(pos.upper(), pos.upper())
	    if pos is None: continue
	    lemma = lemma.decode('latin-1')

	    sent = sent_map.get(value.lower(), 0)
	    intense = intense_map.get(value.lower(), 0)

	    print lemma, pos, sent, intense
	    
	    if sent or intense:
	    
		l = get_or_create(Lemma, language=language,
				  pos=pos, lemma=lemma)

		SentimentLemma.objects.create(lexicon=lex, lemma=l,
					      sentiment=sent, intensifier=intense)
	    
	    

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
