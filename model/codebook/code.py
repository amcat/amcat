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
    
    #functions = ForeignKey(Function) # TODO: create reverse in Function f

    class Meta():
        db_table = 'codes'
        app_label = 'amcat'

    @property
    def label(self):
        return self.labels.all().order_by('language__id')[0].label
        lang = toolkit.head(sorted(self.labels.keys()))
        if lang: return self.labels[lang]
        return repr(self)

    def getLabel(self, lan, fallback=True):
        """
        @param lan: language to get label for
        @type lan: Language object or int
        @param fallback: If True, return another label if language not found
        """
        if type(lan) == int: lan = Language.objects.get(pk=lan)

        try:
            return self.labels.get(language=lan).label
        except Label.DoesNotExist:
            if fallback:
                return self.label
            


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
        # fallback with 'unknown' language
        l2 = Language.objects.create()
        self.assertEqual(o.getLabel(l2), "bla")
        # second label
        Label.objects.create(code=o, language=l2, label="blx")
        self.assertEqual(o.getLabel(l2), "blx")
        self.assertEqual(o.getLabel(Language.objects.create()), "bla")

        self.assertEqual(o.label, "bla")
