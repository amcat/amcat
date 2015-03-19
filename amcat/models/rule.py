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
from django.db import models
import logging
import re
log = logging.getLogger(__name__)


class RuleSet(AmcatModel):

    """
    Class representing a set of syntax transformation rule
    """

    id = models.AutoField(primary_key=True, db_column="rule_id")
    label = models.CharField(max_length=255)
    preprocessing = models.CharField(max_length=1000)

    lexicon_codebook = models.ForeignKey("amcat.codebook", related_name="+")
    lexicon_language = models.ForeignKey("amcat.language", related_name="+")

    def get_lexicon(self):
        cb = self.lexicon_codebook
        cb.cache_labels()
        for code in cb.get_codes():
            labels = {label.language:
                      label.label for label in code.labels.all()}
            lemmata = labels.get(self.lexicon_language, '').strip()
            if lemmata:
                lemmata = re.split("[ ,]+", lemmata)
                for lang, label in labels.iteritems():
                    if lang != self.lexicon_language:
                        yield {"lexclass": label, "lemma": lemmata}

    def get_rules(self):
        for rule in self.rules.order_by("order"):
            result = {"condition": rule.where}
            if rule.insert:
                result['insert'] = rule.insert
            if rule.remove:
                result['remove'] = rule.remove
            if rule.remarks:
                result['remarks'] = rule.remarks
            if rule.display:
                result['display'] = rule.display
            result['order'] = rule.order
            result['label'] = rule.label

            yield result

    def get_ruleset(self):
        r = {"lexicon": list(self.get_lexicon()),
             "rules": list(self.get_rules())}
        if self.preprocessing.strip():
            r["preprocessing"] = self.preprocessing.strip()
        return r

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

