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

# Monkey patch filterset for autofield - no idea why it's not in that list
filterset.FILTER_FOR_DBFIELD_DEFAULTS[models.AutoField] = dict(filter_class=NumberFilter)

from django.forms import ValidationError

import logging; log = logging.getLogger(__name__) 

ORDER_BY_FIELD = "order_by"

class AmCATFilterBackend(filters.DjangoFilterBackend):
    def get_filter_class(self, view):
        filter_fields = tuple(view.get_filter_fields())

        class AutoFilterSet(filterset.FilterSet):
            pk = NumberFilter(name='id')

            # This overrides the default FilterSet value
            order_by_field = ORDER_BY_FIELD

            def __len__(self):
                return count.count(self.qs)

            def get_order_by_fields(self):
                """
                Get order_by fields based on current request.
                """
                if not self.data: return

                for ofield in self.data.getlist(ORDER_BY_FIELD):
                    # We use '-' and '?' for ordering descending or randomly
                    # respectively
                    desc = ofield.startswith(("-", "?"))

                    if (ofield[1:] if desc else ofield) in self._meta.fields:
                        yield ofield

            def get_ordered_fields(self):
                """
                Same as get_order_by_fields, but it does not includes the direction
                of ordering.
                """
                for f in self.get_order_by_fields():
                    yield f[1:] if f.startswith(("-", "?")) else f

            def _order_by(self, qs):
                """
                Order results according to allowed values in Meta class, and
                the value given by the client.
                """
                if not hasattr(self.data, "getlist"):
                    # Empty query parameters
                    return qs

                return qs.order_by(*self.get_order_by_fields())

            def _filter(self, qs):
                """
                Filter all fields based on given filters.
                """
                for name, filter_ in self.filters.iteritems():
                    qs = self._filter_field(qs, name, filter_)

                return qs

            def _filter_field(self, qs, name, filter_):
                """
                Filter specific field
                """
                data = self.data.getlist(name) if hasattr(self.data, 'getlist') else []
                data = data or [self.form.initial.get(name, self.form[name].field.initial)]

                # Filter all given fields OR'ed.
                q = models.Q()
                for value in data:
                    # To filter on model properties which are None, provide
                    # null as argument.
                    if value == "null" and name.endswith("__id"):
                        q = q | models.Q(**{ name[0:-4] : None })
                        continue

                    try:
                        value = self.form.fields[name].clean(value)
                    except ValidationError:
                        continue
                    else:
                        if value == []: continue

                    # Do not filter when value is None or an empty string
                    if (isinstance(value, basestring) and not value) or value is None:
                        continue

                    q = q | models.Q(**{ name : value })

                return qs.filter(q)

            @property
            def qs(self):
                """
                By default, filterset.Filterset does not allow for multiple
                GET arguments with the same identifier. This results in being
                unable to get a specific set of objects based on their id. For
                example:

                  ?id=1&id=2

                wouldn't work. We override qs to provide this function, while
                keeping the same overall tactics of super.qs.
                """
                if hasattr(self, '_qs'):
                    return self._qs

                # No caches queryset has been found, try to create one by
                # filtering, followed by ordering.
                self._qs = self.queryset.all()
                self._qs = self._filter(self._qs)
                self._qs = self._order_by(self._qs)

                # Only return non-duplicates
                if can_distinct_on_pk(self._qs):
                    # Postgres (and other databases) only allow distinct when
                    # no ordering is specified, or if the first order-column
                    # is the same as the one you're 'distincting' on.
                    self._qs = self._qs.distinct("pk")
                else:
                    # Use naive way of defining distinct. The database has to
                    # iterate over all rows (well, not in theory, but postgres
                    # does..)
                    self._qs = self._qs.distinct()
                    
                return self.qs

            class Meta:
                model = view.model
                fields = filter_fields

        return AutoFilterSet

    def filter_queryset(self, request, queryset, view):
        return super(AmCATFilterBackend, self).filter_queryset(request, queryset, view)

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
        self.assertEqual(self._get_ids(ProjectResource, id=[p.id, p2.id]), {p2.id, p.id})

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

        
