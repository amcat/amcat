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
Model module representing codebook Codes
"""

from __future__ import unicode_literals, print_function, absolute_import

from django.db import models

from amcat.tools.model import AmcatModel
from amcat.tools import toolkit
from amcat.model.language import Language

from datetime import datetime

import logging; log = logging.getLogger(__name__)

PARTYMEMBER_FUNCTIONID = 0
  
class Code(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='code_id')
    
    class Meta():
        db_table = 'codes'
        app_label = 'amcat'

    @property
    def label(self):
        try:
            return self.labels.all().order_by('language__id')[0].label
        except IndexError:
            return '<{0.__class__.__name__}: {0.id}>'.format(self)
            return repr(super(AmcatModel, self))
        
    def __unicode__(self):
        return self.label
    
    def get_label(self, lan, fallback=True):
        """
        @param lan: language to get label for
        @type lan: Language object or int
        @param fallback: If True, return another label if language not found
        @return: string or None
        """
        if type(lan) == int: lan = Language.objects.get(pk=lan)

        try:
            return self.labels.get(language=lan).label
        except Label.DoesNotExist:
            if fallback:
                try:
                    return self.labels.all().order_by('language__id')[0].label
                except IndexError:
                    return None


    def add_label(self, language, label):
        Label.objects.create(language=language, label=label, code=self)
        


class Label(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='label_id')
    label = models.TextField(blank=False,null=False)

    code = models.ForeignKey(Code, db_index=True, related_name="labels")
    language = models.ForeignKey(Language, db_index=True, related_name="+")


    class Meta():
        db_table = 'labels'
        app_label = 'amcat'




###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCode(amcattest.PolicyTestCase):
    def test_label(self):
        """Can we create objects and assign labels?"""
        # simple label
        o = amcattest.create_test_code(label="bla")
        self.assertEqual(o.label, "bla")
        self.assertEqual(unicode(o), o.label)
        # fallback with 'unknown' language
        l2 = Language.objects.create()
        self.assertEqual(o.get_label(l2), "bla")
        # second label
        Label.objects.create(code=o, language=l2, label="blx")
        self.assertEqual(o.get_label(l2), "blx")
        self.assertEqual(o.get_label(Language.objects.create()), "bla")
        self.assertEqual(o.label, "bla")

        # does .label return something sensible on objects without labels?
        o2 = Code.objects.create()
        self.assertRegexpMatches(o2.label, r'^<Code: \d+>$')
        self.assertIsNone(o2.get_label(l2))

        # does .label and .get_label return a unicode object under all circumstances
        self.assertIsInstance(o.label, unicode)
        self.assertIsInstance(o.get_label(l2), unicode)
        self.assertIsInstance(o2.label, unicode)
