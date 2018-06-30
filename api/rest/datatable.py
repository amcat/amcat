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
import hashlib
import copy
import json
import logging
import types
import collections
import inspect
from itertools import chain
from urllib.parse import urlencode

from django.core.exceptions import ImproperlyConfigured
from django.db.models.query import QuerySet
from django.db.models import Model
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import get_template

from amcat.tools.caching import cached
from api.rest.resources import get_resource_for_model, AmCATResource
from api.rest import filters


FILTER_FIELDS = {
    # Resource : set(fields)
}

ORDERING_FIELDS = {
    # Resource : set(fields)
}

FIELDS_EMPTY = (None, [])
log = logging.getLogger(__name__)


def order_by(field):
    """
    Convert a field with sorting markup (+, -) to a list, which can be
    used in aaSorting (datatables)
    """
    return (
        (field[1:] if field.startswith(("+", "-")) else field),
        ("desc" if field.startswith("-") else "asc")
    )


def _get_valid_fields(queryset, view):
    """
    This is a copy of a part of OrderingFilter.remove_invalid_fields(). It
    determines which fields are orderable. A pull request is pending for
    djangorestframework which would remove this function:

       https://github.com/tomchristie/django-rest-framework/pull/1709

    TODO: Remove function.
    """
    valid_fields = getattr(view, 'ordering_fields', None)

    if valid_fields is None:
        # Default to allowing filtering on serializer fields
        serializer_class = (
            getattr(view, 'serializer_class') or
            view.get_serializer_class())

        if serializer_class is None:
            msg = ("Cannot use %s on a view which does not have either a "
                   "'serializer_class' or 'ordering_fields' attribute.")
            import pdb; pdb.set_trace()
            raise ImproperlyConfigured(msg % view.__class__.__name__)

        valid_fields = [
            field.source or field_name
            for field_name, field in serializer_class().fields.items()
            if not getattr(field, 'write_only', False)
        ]

    elif valid_fields == '__all__':
        # View explictly allows filtering on any model field
        valid_fields = [field.name for field in queryset.model._meta.fields]
        valid_fields += queryset.query.aggregates.keys()

    return set(valid_fields)


def get_valid_fields(queryset, view):
    """Caching wrapper around _get_valid_fields()"""
    # Can we get results from cache?
    if view.__class__ in ORDERING_FIELDS:
        return ORDERING_FIELDS[view.__class__]

    # Put results in cache and return
    fields = _get_valid_fields(queryset, view)
    ORDERING_FIELDS[view.__class__] = fields
    return fields


class Datatable(object):
    """
    Create HTML / Javascript code for a table based on `handler`. Optional
    options may be passed as `options` according to:

    http://www.datatables.net/usage/options

    TODO: Remove Resource-references
    """

    def __init__(self, resource, rowlink=None, rowlink_open_in="same", options=None, hidden=None, url=None,
                 ordering=None, format="json", filters=None, checkboxes=False, allow_html_export=False,
                 allow_export_via_post=False, extra_args=None, url_kwargs=()):
        """
        Default ordering is "id" if possible.

        @param resource: handler to base datatable on
        @type resource: AmCATResource

        @param hidden: hidden fields
        @type hidden: set

        @param filters: an optional list of selector/value pairs for filtering
        @param extra_args: an optional list of field/value pairs for extra 'get' options
        @param url_kwargs: if a ViewSet is given, also provide url_kwargs which are used to determine the url

        @param checkboxes: indicates whether checkboxes should be displayed
        @type checkboxes: bool

        @param allow_html_export: display 'xhtml' as export option
        @type allow_html_export: bool
        """
        if inspect.isclass(resource) and issubclass(resource, Model):
            resource = get_resource_for_model(resource)
        self.resource = resource() if callable(resource) else resource

        self.options = options or dict()
        self.rowlink = rowlink or getattr(self.resource, "get_rowlink", lambda: None)()
        self.rowlink_open_in = rowlink_open_in
        self.ordering = ordering
        self.checkboxes = checkboxes
        self.allow_html_export = allow_html_export
        self.allow_export_via_post = allow_export_via_post

        self.format = format
        self.hidden = set(hidden) if isinstance(hidden, collections.Iterable) else set()
        self.filters = filters or []  # list of name : value tuples for filtering
        self.extra_args = extra_args or []  # list of name : value tuples for GET arguments

        if url is None:
            if isinstance(self.resource, AmCATResource):
                url = self.resource.url
            else:
                url = self.resource.get_url(**dict(url_kwargs))
        self.base_url = url

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

        It is now implemented as the hash of `self.url` prepended with the character
        'd'. This prevents names from becoming too long.
        """
        return "d" + hashlib.sha256(self.url.encode("utf-8")).hexdigest()

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
        if isinstance(self.resource, AmCATResource):
            fields = list(self.resource.get_field_names())
        else:
            # ViewSet
            fields = list(self.resource.get_serializer_class()().fields.keys())

        if hasattr(self.resource, 'extra_fields'):
            fields += self.resource.extra_fields(self.extra_args)

        for field in self.hidden:
            if field in fields:
                fields.remove(field)

        for field in fields:
            yield str(field)

    @property
    @cached
    def fields(self):
        return list(self.get_fields())

    def _get_copy_kwargs(self, **kwargs):
        kws = {
            'rowlink': self.rowlink,
            'rowlink_open_in': self.rowlink_open_in,
            'options': self.options,
            'hidden': self.hidden,
            'url': self.base_url,
            'ordering': self.ordering,
            'filters': self.filters,
            'extra_args': self.extra_args,
            'format': self.format,
            'checkboxes': self.checkboxes,
            'allow_html_export': self.allow_html_export
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
        options['searching'] = bool(getattr(self.resource, "search_fields", None))

        return get_template('api/datatables.js.html').render({
            'id': self.name,
            'rowlink': self.rowlink,
            'rowlink_open_in': self.rowlink_open_in,
            'url': self.url,
            'allow_export_via_post': self.allow_export_via_post,
            'options': json.dumps(options),
            'checkboxes': self.checkboxes
        })

    def get_aoColumns(self):
        """Returns a list with (default) columns."""
        return self.options.get('aoColumns', [{
            "mData": str(n),
            "bSortable": self.can_order_by(n)
        } for n in self.fields])

    def get_aoColumnDefs(self):
        """Use this method to override when providing special colums"""
        return []

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
        replace = lambda arg: (ID_REPLACE_NUMBER if arg == '{id}' else arg)
        if args: args = [replace(arg) for arg in args]
        if kwargs: kwargs = {k: replace(v) for k, v in kwargs.items()}

        url = reverse(viewname, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)
        url = url.replace(str(ID_REPLACE_NUMBER), '{id}')

        return self.copy(rowlink=url)

    def _get_filter_class(self):
        # There is probably a more standard way to do this        
        r = self.resource
        try:
            fc = r.filter_class
        except AttributeError:
            fc = filters.DjangoPrimaryKeyFilterBackend().get_filter_class(r, queryset=r.model.objects.all())
        return fc()

    def can_order_by(self, field):
        # We can't sort if this is not backed by a DBMS
        if self.resource.model is None:
            return False

        valid = get_valid_fields(self.resource.model.objects.none(), self.resource)
        return order_by(field)[0] in valid

    def can_filter(self, field):
        return any(f == field for f in self._get_filter_class().filters.keys())

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
            if not self.can_order_by(field):
                raise ValueError("Cannot order by field '{}', column does not exist on this table".format(field))

        return self.copy(ordering=tuple(fields))

    def _filter(self, selector, value, check_can_filter=True):
        """
        @param selector: field to filter on, including filter type (name__iexact, for example)
        @param value: value to filter on
        @type value: QuerySet, list, tuple, generator, Model, str, int
        """
        if isinstance(value, QuerySet):
            return self._filter(selector, list(value), check_can_filter=check_can_filter)

        if isinstance(value, (list, tuple, types.GeneratorType)):
            selector = selector[:-4] if selector.endswith('__in') else selector
            return "&".join([self._filter(selector, v, check_can_filter=check_can_filter) for v in value])

        if isinstance(value, Model):
            return self._filter(selector + '__%s' % value._meta.pk.attname, value.pk, check_can_filter=check_can_filter)

        return urlencode({selector: value})

    def filter(self, **filters):
        """
        Filter on specific fields. You can use Django-style QuerySet filtering. For
        example, you can do:

            dt = Datatable(ProjectResource).filter(name__icontains='someting')

        And in a template:

            {{ dt|safe }}

        """
        new_filters = list(chain(self.filters, filters.items()))
        return self.copy(filters=new_filters)

    def add_arguments(self, **args):
        """
        Add additional 'GET' arguments, e.g. cols or search queries 
        """
        extra_args = list(chain(self.extra_args, args.items()))
        return self.copy(extra_args=extra_args)

    def set_format(self, format):
        return self.copy(format=format)

    @property
    def url(self):
        url = self.base_url
        url += "?format=" + self.format
        url += "".join(['&%s' % self._filter(sel, val) for (sel, val) in self.filters])
        url += "".join(['&%s' % self._filter(sel, val, check_can_filter=False) for (sel, val) in self.extra_args])
        return url

    def __str__(self):
        links = {}
        for fmt in ["api", "csv", "json", "xlsx", "spss", "xhtml"]:
            t = self.set_format(fmt)
            if fmt != "api": t = t.add_arguments(page_size=999999)
            links[fmt] = t.url
        return get_template('api/datatables.html').render({
            'js': self.get_js(),
            'id': self.name,
            'cols': self.fields,
            'links': links,
            'allow_html_export': self.allow_html_export
        })

    def __repr__(self):
        return u"DataTable(%r)" % self.resource

