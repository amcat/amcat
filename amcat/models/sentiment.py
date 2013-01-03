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
from amcat.tools.model import AmcatModel
from django.db import models

from amcat.models.language import Language
from amcat.models.word import Lemma

class SentimentLexicon(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='lexicon_id')
    language = models.ForeignKey(Language)
    label = models.CharField(max_length=500)

    class Meta():
        db_table = 'sentimentlexica'
        app_label = 'amcat'

class SentimentLemma(AmcatModel):
    id = models.AutoField(primary_key=True)
    lexicon = models.ForeignKey(SentimentLexicon)
    lemma = models.ForeignKey(Lemma)

    sentiment = models.FloatField()
    intensifier = models.FloatField()

    class Meta():
	db_table = 'sentiment_lemmata'
        app_label = 'amcat'

