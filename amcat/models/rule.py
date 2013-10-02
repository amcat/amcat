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
Model module containing the Article class representing documents in the
articles database table.
"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.tools.model import AmcatModel
from amcat.models import Label
from django.db import models
from collections import defaultdict
import logging
import re
log = logging.getLogger(__name__)


class RuleSet(AmcatModel):
    """
    Class representing a set of syntax transformation rule
    """
    id = models.AutoField(primary_key=True, db_column="rule_id")
    label = models.CharField(max_length=255)

    lexicon_codebook = models.ForeignKey("amcat.codebook", related_name="+")
    lexicon_language = models.ForeignKey("amcat.language", related_name="+")


    @property
    def lexicon(self):
        """Return a lemma : {lexclass, ..} dictionary"""
        
        SOLR_KEYWORD_SET = {"AND", "OR", "NOT"}
        def _get_lexical_entries(label):
            return set(re.findall("[\w*]+", label)) - SOLR_KEYWORD_SET
        lexicon = getattr(self, "_cached_lexicon", None)
        if lexicon is None:
            lexicon = {}
            labels = Label.objects.filter(code__codebook_codes__codebook=self.lexicon_codebook)
            all_labels = defaultdict(list)
            for label in labels:
                all_labels[label.code_id].append(label)
            codes = {code_id : sorted(labels, key=lambda l:l.language_id)[0].label
                     for (code_id, labels) in all_labels.items()}

            lexicon = defaultdict(set)
            for label in labels:
                if label.language_id == self.lexicon_language.id:
                    for lemma in _get_lexical_entries(label.label):
                        lexicon[lemma].add(codes[label.code_id])
            self._cached_lexicon = lexicon
        return lexicon
        
    
    class Meta():
        db_table = 'rulesets'
        app_label = 'amcat'

class Rule(AmcatModel):
    """
    Class representing a syntax transformation rule
    """
    id = models.AutoField(primary_key=True, db_column="rule_id")

    label = models.CharField(max_length=255)

    ruleset = models.ForeignKey(RuleSet, related_name="rules")
    order = models.IntegerField()

    display = models.BooleanField(default=False)
    where = models.TextField()
    insert = models.TextField(null=True, blank=True)
    remove = models.TextField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    class Meta():
        db_table = 'rules'
        app_label = 'amcat'
        ordering = ['ruleset', 'order']
