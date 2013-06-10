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
AmCAT-specific adaptations to rest_framework filters
(using django_filters)
activated by settings.REST_FRAMEWORK['FILTER_BACKEND']
"""
from api.rest import count
from amcat.tools.djangotoolkit import can_distinct_on_pk

from rest_framework import filters
from django_filters import filterset
from django_filters.filters import Filter

from django_filters.filters import NumberFilter
from django.db import models
from django import forms
# Monkey patch filterset for autofield - no idea why it's not in that list
filterset.FILTER_FOR_DBFIELD_DEFAULTS[models.AutoField] = dict(filter_class=NumberFilter)

from django.forms import ValidationError

import logging; log = logging.getLogger(__name__) 

ORDER_BY_FIELD = "order_by"

class InFilter(filterset.ModelMultipleChoiceFilter):
    """Filter for {'pk':[1,2,3]} / pk=1&pk=2 queries"""

    def filter(self, qs, value):
        if not value: return qs
        values = [obj.id for obj in value]
        return qs.filter(**{'%s__in' % (self.name): value})

class AmCATFilterSet(filterset.FilterSet):
    """
    - Allow descending /  ascending order
    - Allow filtering on pk and ordering by default
    """
    
    pk = InFilter(name='id', queryset=None)

    # This overrides the default FilterSet value
    order_by_field = ORDER_BY_FIELD

    def __init__(self, *args, **kargs):
        super(AmCATFilterSet, self).__init__(*args, **kargs)
        self.filters["pk"].field.queryset = self.queryset
    
    def __len__(self):
        """Default implementation does len(self.qs)  which runs the whole query..."""
        return count.count(self.qs)

    def get_ordering_field(self):
        """
        - Add descending order (-field) to the list of valid choices
        - Make MultipleChoiceField to allow for ordering on more than one field
          (requires changing the order_by behaviour in qs below)
        """
        field = super(AmCATFilterSet, self).get_ordering_field()
        if field:
            choices = field.choices + [("-"+key, label + " (Desc)") for (key, label) in field.choices]
            return forms.MultipleChoiceField(label=field.label, required=field.required, choices=choices)
        return field

    @property
    def qs(self):
        # 'Monkey patch' to allow order by to take muliple values from MultipleChoiceField
        # function is copy/paste from filterset.py except for import, order_by, and silent validation exceptions
        from django.utils import six
        if not hasattr(self, '_qs'):
            qs = self.queryset.all()
            for name, filter_ in six.iteritems(self.filters):
                try:
                    if self.is_bound:
                        data = self.form[name].data
                    else:
                        data = self.form.initial.get(
                            name, self.form[name].field.initial)
                    # change    
                    val = None if data == 'null' else self.form.fields[name].clean(data)
                    # end of change
                    qs = filter_.filter(qs, val)
                except forms.ValidationError:
                    raise# was: pass
            if self._meta.order_by:
                try:
                    order_field = self.form.fields[self.order_by_field]
                    data = self.form[self.order_by_field].data
                    # changes
                    if data and data != ['']:
                        value = order_field.clean(data)
                        if value:
                            qs = qs.order_by(*value)
                    # end of changes
                except forms.ValidationError:
                    raise# was:pass
            self._qs = qs
        return self._qs


class AmCATFilterBackend(filters.DjangoFilterBackend):    
    default_filter_set = AmCATFilterSet
    def get_filter_class(self, view, *args, **kargs):
        
        filter_class = super(AmCATFilterBackend, self).get_filter_class(view, *args, **kargs)
        filter_class._meta.order_by = True
        return filter_class


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
from api.rest.apitestcase import ApiTestCase

class TestFilters(ApiTestCase):    
    def _get_ids(self, resource, rtype=set, **filters):
        result = self.get(resource, **filters)
        return rtype(row['id'] for row in result['results'])

    def test_uniqueness(self):
        from amcat.models import ArticleSet
        from api.rest.resources import ArticleResource

        a1 = amcattest.create_test_article()
        as1 = ArticleSet.objects.create(name="foo", project=a1.project)
        as2 = ArticleSet.objects.create(name="bar", project=a1.project)

        as1.add(a1)
        as2.add(a1)

        arts =  self._get_ids(ArticleResource, list, articlesets_set__id=[as1.id, as2.id])

        self.assertEquals(1, len(arts))


    def test_order_by(self):
        from api.rest.resources import ProjectResource

        p = amcattest.create_test_project(name="a", active=True)
        p2 = amcattest.create_test_project(name="b", active=True)
        p3 = amcattest.create_test_project(name="c", active=False)

        # Ascending order
        res = self.get(ProjectResource, order_by="name")
        self.assertEqual([p["name"] for p in res['results']], ["a", "b", "c"])

        # Descending order
        res = self.get(ProjectResource, order_by="-name")
        self.assertEqual([p["name"] for p in res['results']], ["c", "b", "a"])

        # Multiple order by
        res = self.get(ProjectResource, order_by=["active", "name"])
        self.assertEqual([p["name"] for p in res['results']], ["c", "a", "b"])

        res = self.get(ProjectResource, order_by=["active", "-name"])
        self.assertEqual([p["name"] for p in res['results']], ["c", "b", "a"])
        
    def test_filter(self):
        from amcat.models import Role
        from api.rest.resources import ProjectResource
        r = Role.objects.get(label='admin', projectlevel=True)
        
        p = amcattest.create_test_project(name="test")
        p2 = amcattest.create_test_project(name="not a test", guest_role=r)
        p3 = amcattest.create_test_project(name="anothertest")

        # no filter
        self.assertEqual(self._get_ids(ProjectResource), {p.id, p2.id, p3.id})
        
        # Filter on simple fields: id, pk, and name 
        self.assertEqual(self._get_ids(ProjectResource, id=p2.id), {p2.id})
        self.assertEqual(self._get_ids(ProjectResource, name=p.name), {p.id})
        self.assertEqual(self._get_ids(ProjectResource, pk=p.id), {p.id})

        # Filter on directly related fields
        self.assertEqual(self._get_ids(ProjectResource, guest_role__id=r.id), {p2.id})

        # Filter on 1-to-many field
        #aset = amcattest.create_test_set(project=p)
        #self.assertEqual(self._get_ids(ProjectResource, articlesets_set__id=aset.id), {p.id})
        
        # Filter on more n-on-m field: project roles
        u = amcattest.create_test_user()
        self.assertEqual(self._get_ids(ProjectResource, projectrole__user__id=u.id), set())
        
        from amcat.models import ProjectRole
        ProjectRole.objects.create(project=p3, user=u, role=r)
        self.assertEqual(self._get_ids(ProjectResource, projectrole__user__id=u.id), {p3.id})

        # Filter on multiple values of same key. Expect them to be OR'ed.
        #self.assertEqual(self._get_ids(ProjectResource, id=[p.id, p2.id]), {p2.id, p.id})
        self.assertEqual(self._get_ids(ProjectResource, pk=[p.id, p2.id]), {p2.id, p.id})

    def test_filter_articlemeta(self):
        # Filter on date ranges and make sure normal filters still work
        p = amcattest.create_test_project(name="test")
        a1 = amcattest.create_test_article(project=p, date="2012-01-01")
        a2 = amcattest.create_test_article(project=p, date="2012-02-01")
        a3 = amcattest.create_test_article(project=p, date="2012-03-01")
        from api.rest.resources import ArticleMetaResource


        # filter on article set
        s = amcattest.create_test_set(articles=[a1, a2])
        self.assertEqual(self._get_ids(ArticleMetaResource, articleset=s.id), {a1.id, a2.id})

        # filter on dates
        self.assertEqual(self._get_ids(ArticleMetaResource, project=p.id), {a1.id, a2.id, a3.id})
        self.assertEqual(self._get_ids(ArticleMetaResource, project=p.id, date='2012-01-01'), {a1.id})
        self.assertEqual(self._get_ids(ArticleMetaResource, project=p.id, date_from='2012-01-15'), {a2.id, a3.id})
        self.assertEqual(self._get_ids(ArticleMetaResource, project=p.id, date_to='2012-01-15'), {a1.id})

        # Filter on multiple pk values
        #self.assertEqual(self._get_ids(ArticleMetaResource, pk_in=",".join(map(str, [a1.id, a2.id]))), {a1.id, a2.id})
        self.assertEqual(self._get_ids(ArticleMetaResource, pk=[a1.id, a2.id]), {a1.id, a2.id})
        
    def _assertEqualIDs(self, resource, ids, **filters):
        self.assertEqual(self._get_ids(resource, **filters), ids)

    def test_datatables_echo(self):
        from api.rest.resources import ProjectResource

        res = self.get(ProjectResource, datatables_options='{"sEcho":"3"}')
        self.assertEqual(res['echo'], "3")

    def todo_test_datatables_search(self):
        """
        Not yet implemented.
        """
        from api.rest.resources import ProjectResource

        p = amcattest.create_test_project(name="test")
        p2 = amcattest.create_test_project(name="not a test")

        self._assertEqualIDs(
                ProjectResource, {p2.id},
                datatables_options='{"sSearch":"not"}'
        )

        # Test totals
        res = self.get(ProjectResource, datatables_options='{}')
        self.assertEqual(res['total'], 2)
        self.assertEqual(res['subtotal'], 2)

        res = self.get(ProjectResource, datatables_options='{"sSearch":"not"}')
        self.assertEqual(res['total'], 2)
        self.assertEqual(res['subtotal'], 1)

        
