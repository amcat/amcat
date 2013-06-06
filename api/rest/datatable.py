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
import copy

from django.db.models.query import QuerySet
from django.db.models import Model
from django.conf import settings
from django.core.urlresolvers import reverse

from django.template import Context
from django.template.loader import get_template

import logging; log=logging.getLogger(__name__)

import json, types, collections, re

from amcat.tools.caching import cached
import inspect
from api.rest.resources import get_resource_for_model

FIELDS_EMPTY = (None, [])

def order_by(field):
    """
    Convert a field with sorting markup (+, -) to a list, which can be
    used in aaSorting (datatables)
    """
    return (
        (field[1:] if field.startswith(("+", "-")) else field),
        ("desc" if field.startswith("-") else "asc")
    )

class Datatable(object):
    """
    Create HTML / Javascript code for a table based on `handler`. Optional
    options may be passed as `options` according to:

    http://www.datatables.net/usage/options
    """
    def __init__(self, resource, rowlink=None, options=None, hidden=None, url=None, ordering=None):
        """
        Default ordering is "id" if possible.

        @param resource: handler to base datatable on
        @type resource: AmCATResource

        @param hidden: hidden fields
        @type hidden: set
        """
        if inspect.isclass(resource) and issubclass(resource, Model):
            resource = get_resource_for_model(resource)
        self.resource = resource() if callable(resource) else resource
            
        self.options = options or dict()
        self.rowlink = rowlink or getattr(self.resource, "get_rowlink", lambda  : None)()
        self.ordering = ordering

        self.hidden = set(hidden) if isinstance(hidden, collections.Iterable) else set()
        self.url = url

        if self.url is None:
            self.url =  "{self.resource.url}?format=json".format(**locals())

    @property
    def name(self):
        return self.get_name()

    def get_name(self):
        """
        Generate a name, based on url. The returned value follows the
        following constraints:

          - Must begin with a letter ([A-Za-z])
          - Followed by any number of
            - letters
            - digits ([0-9])
            - hyphens ("-")
            - underscores ("_")
            - colons (":")
            - and periods (".").
        """
        return "d" + re.sub(r'[^0-9A-Za-z_:.-]', '__', self.url)

    def get_default_ordering(self):
        return ("-id",) if "id" in self.get_fields() else ()

    def get_fields(self):
        """
        Calculate fields based on:

            * hidden fields
            * resource._meta.fields
            * default fields

        Returns, if possible, in the order specified in _meta.
        """
        fields = list(self.resource.get_field_names())
        fields = [f for f in fields if f not in self.hidden]

        if not self.resource.get_serializer_class()().opts.fields and \
                hasattr(self.resource, "model") and self.resource.model:
            # Try to keep order defined on model if and only if fields
            # is not explicitly defined.
            ofields = []

            for field in self.resource.model._meta.fields:
                if field.name in fields:
                    fields.remove(field.name)
                    yield field.name

        for field in fields:
            yield field

    @property
    @cached
    def fields(self):
        return list(self.get_fields())

    def _get_copy_kwargs(self, **kwargs):
        kws = {
            'rowlink' : self.rowlink,
            'options' : self.options,
            'hidden' : self.hidden,
            'url' : self.url,
            'ordering' : self.ordering
        }
        kws.update(kwargs)
        return kws
    
    def copy(self, **kwargs):
        """
        If called with no keyword arguments, this method will return a copy
        of this object. All given keyword arguments will be passed to the
        constructor of the new object.
        """
        kwargs = self._get_copy_kwargs(**kwargs)
        return self.__class__(resource=self.resource, **kwargs)
    

    def get_js(self):
        """Returns a string with rendered javascript"""
        ordering = self.ordering
        if ordering is None:
            ordering = self.get_default_ordering()

        options = copy.copy(self.options)
        options['aaSorting'] = [list(order_by(f)) for f in ordering]
        options['aoColumns'] = self.get_aoColumns()
        options['aoColumnDefs'] = self.get_aoColumnDefs()

        return get_template('api/datatables.js.html').render(Context({
            'id' : self.name,
            'rowlink' : self.rowlink,
            'url' : self.url,
            'options' : options
        }))

    def get_aoColumns(self):
        """
        Returns a list with (default) columns.

        @param *cols: extra columns
        """
        return self.options.get('aoColumns', [dict(mData=n) for n in self.fields]) 

    def get_aoColumnDefs(self):
        """Use this method to override when providing special colums"""
        return []

    def _filter(self, selector, value):
        """
        @param selector: field to filter on, including filter type (name__iexact, for example)
        @param value: value to filter on
        @type value: QuerySet, list, tuple, generator, Model, str, int
        """
        if isinstance(value, QuerySet):
            return self._filter(selector, list(value))

        if isinstance(value, (list, tuple, types.GeneratorType)):
            selector = selector[:-4] if selector.endswith('__in') else selector
            return "&".join([self._filter(selector, v) for v in value])

        if isinstance(value, Model):
            return self._filter(selector + '__%s' % value._meta.pk.attname, value.pk)

        # Determine if filtering on selector is allowed
        if selector not in self.resource.get_filter_fields():
            raise ValueError("Filtering on field '{selector}' is not allowed on '{self}'".format(**locals()))

        return '%s=%s' % (selector, value)

    ### PUBLIC ###
    def hide(self, *columns):
        """
        Hide given columns. For example:

            dt.hide('name', 'description')

        """
        return self.copy(hidden=self.hidden | set(columns))

    def rowlink_reverse(self, viewname, urlconf=None, args=None, kwargs=None, current_app=None):
        """
        Rowlink this table to the 'reverse' of the view.
        Use '{id}' for the arg of kwarg you want to be tied to the row id.
        """
        # do funky replacing with a number because the urls generally want numers
        # any better idea would be, ehm, a better idea
        # but at least this concentrates the badness in one place instead of hard
        # coding absolute urls all over the view code
        ID_REPLACE_NUMBER = 9999999999
        replace = lambda arg: (ID_REPLACE_NUMBER if arg=='{id}' else arg)
        if args: args = [replace(arg) for arg in args]
        if kwargs: kwargs = {k : replace(v) for k,v in kwargs.iteritems()}

        url = reverse(viewname, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)
        url = url.replace(str(ID_REPLACE_NUMBER), '{id}')
        
        return self.copy(rowlink = url)

        
    def order_by(self, *fields):
        """
        Order this table by given columns. This will overwrite previous
        order_by() calls.
        """
        # Check fields for validity
        for field in fields:
            # Check for illegal ordering
            if field.startswith("?"):
                raise ValueError("Random ordering not yet supported ({})".format(field))

            # Check for existance of field
            field = field[1:] if field.startswith(("+", "-")) else field
            if field not in self.fields:
                raise ValueError("Cannot order by field '{}', column does not exist on this table".format(field))

        return self.copy(ordering=tuple(fields))

    def filter(self, **filters):
        """
        Filter on specific fields. You can use Django-style QuerySet filtering. For
        example, you can do:

            dt = Datatable(ProjectResource).filter(name__icontains='someting')

        And in a template:

            {{ dt|safe }}

        """
        url = self.url
        url += "".join(['&%s' % self._filter(*f) for f in filters.items()])

        return self.copy(url=url)

    def __unicode__(self):
        return get_template('api/datatables.html').render(Context({
            'js' : self.get_js(),
            'id' : self.name,
            'cols' : self.fields
        }))

    def __repr__(self):
        return u"DataTable(%r)" % self.resource



class ReprString(unicode):
    """Unicode object were __repr__ == __unicode__"""
    def __repr__(self): return unicode(self)

class FavouriteDatatable(Datatable):
    """
    Datatable that renders the favourite column as a star with set/unset actions
    """
    
    def __init__(self, set_url, unset_url, label, *args, **kargs):
        """
        @param set_url: url for the GET request to set a target as favourite
        @param unset_url: url for the GET request to unset a target as favourite
        @param label: name to display in the notification 
        """
        super(FavouriteDatatable, self).__init__(*args, **kargs)
        self.set_url = set_url
        self.unset_url = unset_url
        self.label = label

    def _get_copy_kwargs(self, **kwargs):
        kw = super(FavouriteDatatable, self)._get_copy_kwargs(**kwargs)
        kw.update(dict(set_url=self.set_url, unset_url=self.unset_url, label=self.label))
        return kw
        
    def get_aoColumnDefs(self):
        template = get_template("api/favourite.js")
        js = template.render(Context(self.__dict__))
        return {
            "aTargets" : ["favourite"],
            "mRender" : ReprString(js),
        }
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestDatatable(amcattest.PolicyTestCase):
    PROJECT_FIELDS = {'id', 'name', 'description', 'insert_date', 'owner',
                      'insert_user', 'guest_role', 'active', 'index_default', 'favourite'}

    def test_url(self):
        from api.rest.resources import UserResource
        d = Datatable(UserResource)
        self.assertEqual(d.url, '/api/v4/user?format=json')

    def test_fields(self):
        from api.rest.resources import ProjectResource
        from api.rest.resources.amcatresource import AmCATResource
        from api.rest.serializer import AmCATModelSerializer
        from amcat.models import Project

        d = Datatable(ProjectResource)

        self.assertEqual(set(d.fields), TestDatatable.PROJECT_FIELDS)

        # Test order of fields.
        class TestSerializer(AmCATModelSerializer):
            class Meta:
                model = Project
                fields = ('name', 'description', 'id')

        class TestResource(AmCATResource):
            model = Project
            serializer_class = TestSerializer

        d = Datatable(TestResource)
        self.assertEqual(('name', 'description', 'id'), tuple(d.fields))


    def test_hide(self):
        from api.rest.resources import ProjectResource
        d = Datatable(ProjectResource)

        # Nothing hidden by default
        self.assertEqual(set(d.fields), TestDatatable.PROJECT_FIELDS)

        # Hide some fields..
        hide = {"id", "name", "insert_user"}
        d = d.hide(*hide)

        self.assertEqual(set(d.fields), TestDatatable.PROJECT_FIELDS - hide)

    def test_filter(self):
        from api.rest.resources import UserResource

        d = Datatable(UserResource)
        s = '/api/v4/user?format=json'

        # No filter
        self.assertEqual(d.url, s)

        # One filter
        d = d.filter(id=1)
        self.assertEqual(d.url, s + "&id=1")

        # Multiple filters
        d = d.filter(id=2)
        self.assertEqual(d.url, s + "&id=1&id=2")

        d = Datatable(UserResource).filter(id=[1,2])
        self.assertEqual(d.url, s + "&id=1&id=2")

        # Test wrong filter field
        self.assertRaises(ValueError, lambda:d.filter(foo=1))

    def test_js(self):
        from api.rest.resources import ProjectResource
        d = Datatable(ProjectResource)
        js = d.get_js()

    def test_get_name(self):
        from api.rest.resources import ProjectResource

        d = Datatable(ProjectResource).filter(id=[1, "#$^"])
        self.assertTrue(len(d.get_name()) >= 1)
        self.assertFalse(re.match(r'[^0-9A-Za-z_:.-]', d.get_name()))
        self.assertTrue(re.match(r'^[A-Za-z]', d.get_name()))

    def test_order_by_func(self):
        self.assertEquals(("field", "desc"), order_by("-field"))
        self.assertEquals(("f", "asc"), order_by("+f"))

    def test_order_by(self):
        from api.rest.resources import ProjectResource

        d = Datatable(ProjectResource).order_by("name")
        self.assertTrue("name" in unicode(d))
        self.assertTrue("['name', 'asc']" in unicode(d))
        self.assertTrue("['name', 'desc']" in unicode(d.order_by("-name")))

        with self.assertRaises(ValueError):
            d.order_by("bla")

        with self.assertRaises(ValueError):
            d.order_by("?name")

