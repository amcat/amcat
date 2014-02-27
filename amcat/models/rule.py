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


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest


class TestRules(amcattest.AmCATTestCase):

    def test_lexicon(self):
        from amcat.models import Language
        cb = amcattest.create_test_codebook()
        l1, l2 = [Language.get_or_create(label=x) for x in ["a", 'b']]

        c1 = amcattest.create_test_code(label="a", language=l1)
        c1.add_label(l2, "A")
        cb.add_code(c1)

        c2 = amcattest.create_test_code(label="b", language=l1)
        c2.add_label(l2, "B1, B2")
        cb.add_code(c2)

        r = RuleSet.objects.create(label="test", lexicon_codebook=cb,
                                   lexicon_language=l2)

        result = sorted(r.get_lexicon(), key=lambda l: l['lexclass'])
        self.assertEqual(result, [{"lexclass": "a", "lemma": ["A"]},
                                  {"lexclass": "b", "lemma": ["B1", "B2"]}])

    def test_rules(self):
        cb = amcattest.create_test_codebook()
        lang = amcattest.get_test_language()
        r = RuleSet.objects.create(label="test", lexicon_codebook=cb,
                                   lexicon_language=lang)
        condition = "?x :rel_nsubj ?y"
        insert = "?x :boe ?y"
        Rule.objects.create(ruleset=r, label="x", order=2,
                            where=condition, insert=insert)

        getrules = lambda r : [{k:v for k,v in rule.iteritems()
                                if k in ["condition", "insert"]}
                               for rule in r.get_rules()]

        self.assertEqual(getrules(r),
                         [{"condition": condition, "insert": insert}])

        Rule.objects.create(ruleset=r, label="y", order=1,
                            where="w", insert="i")
        self.assertEqual(getrules(r),
                         [{"condition": "w", "insert": "i"},
                          {"condition": condition, "insert": insert}])
