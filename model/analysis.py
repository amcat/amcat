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
from amcat.model.language import Language
from amcat.model.word import Word

from django.db import models

class Analysis(AmcatModel):
    """Object representing an NLP 'preprocessing' analysis"""
    id = models.IntegerField(db_column='analysis_id', primary_key=True)

    label = models.CharField(max_length=100)
    language = models.ForeignKey(Language)

    def __unicode__(self):
        return self.label
    
    class Meta():
        db_table = 'parses_analyses'
        app_label = 'amcat'

class Relation(AmcatModel):
    id = models.IntegerField(db_column='relation_id', primary_key=True)
    label = models.CharField(max_length=100)
    
    class Meta():
        db_table = 'parses_relations'
        app_label = 'amcat'
    def __unicode__(self):
        return self.label

        
class Pos(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='pos_id')
    major = models.CharField(max_length=100)
    minor = models.CharField(max_length=500)
    pos =  models.CharField(max_length=1, null=True)
        
    class Meta():
        db_table = 'parses_pos'
        app_label = 'amcat'

class Token(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='token_id')

    sentence = models.ForeignKey("amcat.Sentence", related_name="tokens")
    word = models.ForeignKey(Word)
    position = models.IntegerField()
    analysis = models.ForeignKey(Analysis)
    
    class Meta():
        db_table = 'parses_tokens'
        app_label = 'amcat'
    def __unicode__(self):
        return unicode(self.word)


class Triple(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='triple_id')

    parent = models.ForeignKey(Token, related_name="+")
    child = models.ForeignKey(Token, related_name="+")
    relation = models.ForeignKey(Relation)
    analysis = models.ForeignKey(Analysis)
    
    class Meta():
        db_table = 'parses_triples'
        app_label = 'amcat'

