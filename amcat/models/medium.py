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
from __future__ import unicode_literals, print_function, absolute_import

from django.db import models
from django.db.models.query import QuerySet

from amcat.tools.model import AmcatModel

def to_medium_ids(mediums):
    """
    Convert argument to medium ids

    @param mediums: mediums to be processed
    @type mediums: QuerySet | Medium | iterable of Mediums | iterable of medium ids
    @return: iterable of medium ids
    """
    if isinstance(mediums, Medium):
        return (mediums.id,)

    if isinstance(mediums, QuerySet) and mediums.model is Medium:
        return mediums.values_list("id", flat=True)

    return ((m.id if isinstance(m, Medium) else m) for m in mediums)

class MediumSourcetype(AmcatModel):
    id = models.AutoField(primary_key=True, db_column="medium_source_id")
    label = models.CharField(max_length=20)

    class Meta():
        db_table = 'media_sourcetypes'

class Medium(AmcatModel):
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column="medium_id")

    name = models.CharField(max_length=200, unique=True)
    abbrev = models.CharField(max_length=10, null=True, blank=True)
    circulation = models.IntegerField(null=True, blank=True)

    #type = models.ForeignKey(MediumSourcetype, db_column='medium_source_id')
    language = models.ForeignKey("amcat.Language", null=True)

    @classmethod
    def get_by_name(cls, name, ignore_case=True):
        """
        Get a medium by label, accounting for MediumAlias.

        @param label: label to look for
        @param ignore_case: use __iexact
        """
        query = dict(name__iexact=name) if ignore_case else dict(name=name)

        try:
            return Medium.objects.get(**query)
        except Medium.DoesNotExist:
            pass

        try:
            return MediumAlias.objects.get(**query).medium
        except MediumAlias.DoesNotExist:
            raise Medium.DoesNotExist("%s could be found in medium nor medium_dict" % name)

    @classmethod
    def get_or_create(cls, medium_name):
        """
        Finds a medium object or creates a new one if not found
        @type medium name: unicode
        @return: a Medium object (or None if medium_name was None)
        """
        if medium_name is None: return None
        try:
            return cls.get_by_name(medium_name, ignore_case = False)
        except cls.DoesNotExist:
            return cls.objects.create(name = medium_name)

    class Meta():
        db_table = 'media'
        verbose_name_plural = 'media'
        app_label = 'amcat'

class MediumAlias(AmcatModel):
    """
    Provide multiple names per medium. Please use get_by_name on
    Medium to select a medium.
    """
    __label__ = 'name'

    medium = models.ForeignKey(Medium)
    name = models.CharField(max_length=200)

    class Meta():
        db_table = 'media_alias'
        verbose_name_plural = 'media_aliases'
        app_label = 'amcat'

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestMedium(amcattest.PolicyTestCase):

    def test_to_medium_ids(self):
        arts = amcattest.create_test_set(2).articles.all()
        m1, m2 = amcattest.create_test_medium(), amcattest.create_test_medium()
        self.assertEqual(set(to_medium_ids(m1)), {m1.id,})
        self.assertEqual(set(to_medium_ids([m1,m2])), {m1.id, m2.id})
        self.assertEqual(set(to_medium_ids(Medium.objects.filter(id__in=[m1.id, m2.id]))), {m1.id, m2.id})
        self.assertEqual(set(to_medium_ids(arts.values_list("medium__id", flat=True))), {a.medium_id for a in arts})

