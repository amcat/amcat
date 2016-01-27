###########################################################################
# (C) Vrije Universiteit, Amsterdam (the Netherlands)                     #
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
from __future__ import division, unicode_literals, print_function

from decimal import Decimal

from django.test import TestCase

from amcat.models import Medium, CodingSchemaField
from amcat.tools import amcattest
from amcat.tools.aggregate_orm import MediumCategory, AverageValue
from amcat.tools.aggregate_orm.categories import DuplicateLabelError, InvalidReferenceError


class TestMediumCategory(TestCase):
    def test_non_unique_label(self):
        codebook, codes = amcattest.create_test_codebook_with_codes()

        codes["A1"].label = "A"
        codes["A1"].save()

        self.assertRaises(DuplicateLabelError, MediumCategory, codebook=codebook)

    def test_invalid_reference(self):
        codebook, codes = amcattest.create_test_codebook_with_codes()
        Medium.objects.bulk_create(Medium(name=l) for l in codes)

        # Should raise no error..
        MediumCategory(codebook=codebook)

        # Delete one medium, so one reference doesn't exist
        Medium.objects.all()[0].delete()
        self.assertRaises(InvalidReferenceError, MediumCategory, codebook=codebook)

    def test_aggregate(self):
        codebook, codes = amcattest.create_test_codebook_with_codes()
        Medium.objects.bulk_create(Medium(name=l) for l in codes)

        category = MediumCategory(codebook=codebook)
        value = AverageValue(CodingSchemaField())

        # Should all collapse into 'A'
        medium_A   = Medium.objects.get(name="A")
        medium_A1  = Medium.objects.get(name="A1")
        medium_A1b = Medium.objects.get(name="A1b")

        rows = [
            # Medium        count  average
            [medium_A.id,   1,     Decimal(1)  ],
            [medium_A1.id,  2,     Decimal(2)  ],
            [medium_A1b.id, 1,     Decimal(3)]
        ]

        self.assertEqual(
            set(map(tuple, category.aggregate([category], value, rows))),
            {(medium_A.id, 4, Decimal(2))}
        )
