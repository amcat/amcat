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
from __future__ import print_function, absolute_import

"""
Object-layer module containing classes modelling sentences
"""

from django.db import models
from amcat.tools.model import AmcatModel


class Sentence(AmcatModel):
    """Model for sentences.

    A sentence is a natural sentence in an article
    created by sentence boundary detection. Manual coding and preprocessing
    is often based on sentences
    """
    __label__ = 'sentence'
    
    id = models.AutoField(primary_key=True, db_column="sentence_id")
    sentence = models.TextField()
    parnr = models.IntegerField()
    sentnr = models.IntegerField()
    article = models.ForeignKey("amcat.Article", related_name='sentences')

    class Meta():
        db_table = 'sentences'
        app_label = 'amcat'
        unique_together = ('article', 'parnr', 'sentnr')
        ordering = ['article', 'parnr', 'sentnr']
    
