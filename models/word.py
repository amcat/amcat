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
from amcat.tools.djangotoolkit import get_or_create
from django.db import models

class Lemma(AmcatModel):
    __label__ = 'lemma'

    id = models.AutoField(primary_key=True, db_column='lemma_id')

    pos = models.CharField(max_length=1)
    lemma = models.CharField(max_length=500)
    language = models.ForeignKey("amcat.Language", related_name="+")
    
    class Meta():
        db_table = 'words_lemmata'

    class Meta():
        db_table = 'words_lemmata'
        app_label = 'amcat'

class Word(AmcatModel):
    __label__ = 'word'

    id = models.AutoField(primary_key=True, db_column='word_id')

    word = models.CharField(max_length=500)
    lemma = models.ForeignKey(Lemma)

    class Meta():
        db_table = 'words_words'
        app_label = 'amcat'

    @classmethod
    def get_or_create(cls, language, lemma, pos, word):
        l = get_or_create(Lemma, language=language, lemma=lemma, pos=pos)
        return get_or_create(cls, word=word, lemma=l)


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestWord(amcattest.PolicyTestCase):
    def test_get_create(self):
        from amcat.models import Language
        l = Language.objects.get(pk=1)
        w = Word.get_or_create(l, "gaan", "V", "ga")
        self.assertEqual(Lemma.objects.get(pk=w.lemma.id).lemma, "gaan")
        self.assertEqual(Word.objects.get(pk=w.id).word, "ga")
        w2 = Word.get_or_create(l, "gaan", "V", "gaat")
        self.assertEqual(w.lemma, w2.lemma)
