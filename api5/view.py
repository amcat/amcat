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
import functools
import logging
import json

from amcat.models import Project, User
from api5.fields import wrap, ColumnListField, OrderingField
from api5.filters import PKFilter, PKInFilter, Filter
from api5.table import build_declared_table, QuerySetTable
from django import forms
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse, HttpResponseBadRequest
from django.views.generic import View
from exportable import DeclaredTable
from exportable.columns import Column
from exportable.exporters import DEFAULT_EXPORTERS, get_exporter_by_extension
from typing import Any, Tuple, Sequence, Union, Container, Dict

from exportable.table import WrappedTable

log = logging.getLogger(__name__)


class BadRequestError(Exception):
    def __init__(self, reason, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reason = reason


class BadRequestFormError(BadRequestError):
    pass


class APIParameterForm(forms.Form):
    _search = forms.CharField(required=False)
    _echo = forms.CharField(required=False)
    _pagination = forms.NullBooleanField(required=False)
    _order_by = OrderingField(required=False)
    _page = forms.IntegerField(required=False, min_value=1)
    _per_page = forms.IntegerField(required=False, min_value=1)
    _include = ColumnListField(required=False)
    _exclude = ColumnListField(required=False)
    _filename = forms.CharField(required=False)
    #_project = forms.ModelChoiceField(required=True, queryset=Project.objects.none())
    _format = forms.ChoiceField(required=False)

    # TODO: implement
    #_scroll_token = forms.CharField()

    def __init__(self, view: "APIView", table: DeclaredTable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table = table
        self.view = view
        self.columns = list(table._get_columns())

        self.fields["_include"].columns = self.columns
        self.fields["_exclude"].columns = self.columns
        self.fields["_order_by"].columns = self.view.get_orderable_columns()
        self.fields["_format"].choices = list(zip(view.get_formats(), view.get_formats()))
        self.fields["_per_page"].max_value = view.max_per_page
        #self.fields["_project"].queryset = Project.objects.all()

    def clean__pagination(self):
        pagination = self.cleaned_data["_pagination"]
        if pagination and not self.view.pagination:
            raise ValidationError("Pagination request, but this API does not support it.")
        if pagination is None:
            return self.view.pagination
        return pagination

    def clean__page(self):
        return self.cleaned_data["_page"] or 1

    def clean__per_page(self):
        return self.cleaned_data["_per_page"] or self.view.per_page

    def clean__format(self):
        return self.cleaned_data["_format"] or "json"

    def clean(self):
        if self.cleaned_data["_include"] and self.cleaned_data["_exclude"]:
            raise ValidationError("You cannot both define _include and _exclude")
        if not self.cleaned_data["_include"] and not self.cleaned_data["_exclude"]:
            self.cleaned_data["_include"] = [self.columns[0]]
        return super().clean()


def gzip_allowed(request: HttpRequest):
    encoding = request.META.get("HTTP_ACCEPT_ENCODING", "")
    return "gzip" in [h.lower().strip() for h in encoding.split(",")]


class APIView(View):
    """

    """
    exporters = DEFAULT_EXPORTERS
    exportable = None

    # Indicate which form to use to check API parameters (parameters starting with _)
    api_parameter_form = APIParameterForm

    # Indicate filter classes (see api5.filters) allowed on this endpoint
    filters = ()  # type: Sequence[Filter]

    # Indicates whether _search parameter is supported on this endpoint
    searchable = False

    # Pagination defaults and settings
    paginator_cls = Paginator
    pagination = True
    max_per_page = 10**6
    per_page = 20

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.page = None
        self.paginator = None

    # HTTP method implementers
    def dispatch(self, request: HttpRequest, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs

        try:
            return super(APIView, self).dispatch(request, *args, **kwargs)
        except BadRequestFormError as e:
            error = dict(type="form", errors=e.reason)
            return HttpResponseBadRequest(json.dumps(error))
        except BadRequestError as e:
            error = dict(type="known", error=e.reason)
            return HttpResponseBadRequest(json.dumps(error))
        except Exception as e:
            log.exception("Unknown exception in dispatch()")
            error = dict(type="unknown", error=str(e))
            return HttpResponseBadRequest(json.dumps(error))

    def get(self, request) -> Union[HttpResponse, StreamingHttpResponse]:
        # Every method assumes that self.objects is present
        self.objects = self.get_objects()
        self.process_objects()
        self.validate_api_args()

        if not self.has_read_permission(self.request.user):
            raise PermissionDenied("You do not have read permissions on this API endpoint.")

        # Build table and export it
        args = self.get_api_arguments()
        table = self.get_exportable()
        exporter = get_exporter_by_extension(args["_format"])()
        compress = gzip_allowed(self.request)
        filename = args["_filename"] or None
        response = exporter.dump_http_response(table, compress=compress, filename=filename)
        for header, value in self.get_response_headers().items():
            response[header] = value
        return response

    def post(self) -> Union[HttpResponse, StreamingHttpResponse]:
        if not self.has_write_permission(self.request.user):
            raise PermissionDenied("You do not have write permissions on this API endpoint.")
        raise NotImplementedError("Not implemented yet.")

    def options(self, **kwargs) -> Union[HttpResponse, StreamingHttpResponse]:
        if not self.has_read_permission(self.request.user):
            raise PermissionDenied("You do not have read permissions on this API endpoint.")
        raise NotImplementedError("Not implemented yet.")

    def get_formats(self) -> Sequence[str]:
        """Returns all supported exportable formats (json, xml, spss)"""
        return [e.extension for e in self.exporters]

    def has_read_permission(self, user: User):
        return True

    def has_write_permission(self, user: User):
        return True

    def get_context(self):
        return None

    def get_objects(self) -> Container[Any]:
        raise NotImplementedError("Subclasses should implement get_objects()")

    def process_objects(self) -> Container[Any]:
        args = self.get_api_arguments()
        objects = self.objects
        objects = self.filter(objects)
        objects = self.order_by(objects, args["_order_by"])

        if self.searchable:
            objects = self.search(objects, args["_search"])

        if args["_pagination"]:
            self.paginator, self.page = self.paginate(objects)
            objects = self.paginator.object_list

        self.objects = objects

    @classmethod
    def get_exportable_class(cls) -> type(WrappedTable):
        return cls.exportable

    def get_exportable(self) -> WrappedTable:
        raise NotImplementedError("Subclasses should implement get_exportable()")

    def search(self, objects: Any, user_input: str):
        raise NotImplementedError("Subclasses should implement search()")

    def order_by(self, objects: Any, order_by: Sequence[Tuple[str, Column]]):
        return objects

    def filter(self, objects: Any):
        filter_map = self.get_filter_map()
        for filter_param in self.get_filter_parameters():
            if filter_param not in filter_map:
                raise BadRequestError("Did not recognize filter: {!r}".format(filter_param))
            objects = filter_map[filter_param].filter(objects, self.request.GET[filter_param])
        return objects

    @functools.lru_cache()
    def get_filter_map(self) -> Dict[str, Filter]:
        return {filter.param: filter for filter in self.get_filters()}

    def get_filters(self) -> Sequence[Filter]:
        return self.filters

    def get_orderable_columns(self):
        return ()

    @classmethod
    def get_columns(cls) -> Sequence[Column]:
        return cls.get_exportable_class()._get_columns()

    def paginate(self, objects: Any):
        api_args = self.get_api_arguments()
        paginator = self.paginator_cls(objects, api_args["_per_page"])
        return paginator, paginator.page(api_args["_page"])

    def get_pagination_headers(self):
        yield "X-API-TOTAL", self.paginator.count
        yield "X-API-PER-PAGE", self.paginator.per_page
        yield "X-API-PAGES", self.paginator.num_pages
        yield "X-API-PAGE", self.page.number

    @wrap(dict)
    def get_response_headers(self) -> dict:
        yield "X-API-ECHO", self.request.GET.get("_echo", "")
        if self.get_api_arguments()["_pagination"]:
            for header, value in self.get_pagination_headers():
                yield header, value

    def get_known_parameters(self):
        return self.api_parameter_form.declared_fields.keys()

    @functools.lru_cache()
    def get_api_arguments(self) -> Dict[str, Any]:
        form = self.api_parameter_form(self, self.get_exportable_class(), data=self.request.GET)

        if not form.is_valid():
            raise BadRequestFormError(form.errors)

        return form.cleaned_data

    def get_filter_parameters(self) -> Sequence[str]:
        return [p for p in self.request.GET if not p.startswith("_")]

    def get_api_parameters(self) -> Sequence[str]:
        return [p for p in self.request.GET if p.startswith("_")]

    def validate_api_args(self) -> None:
        # Any parameter which is present twice (or more) is considered ambiguous
        for p in self.request.GET.keys():
            if len(self.request.GET.getlist(p)) > 1:
                raise BadRequestError("Param {} was given multiple times. This is ambiguous. Bug?".format(repr(p)))

        # Check for unknown
        unknown_parameters = set(self.get_api_parameters()) - set(self.get_known_parameters())
        unknown_parameters = ", ".join(map(repr, sorted(unknown_parameters)))
        if unknown_parameters:
            raise BadRequestError("Did not recognize parameter(s): {}".format(unknown_parameters))

        # Check any static API arguments (such as _format, etc.)
        self.get_api_arguments()


class QuerySetAPIView(APIView):
    model = None
    filters = (
        # Allow filtering on pk by default
        PKFilter(),
        PKInFilter()
    )

    def get_objects(self):
        return self.get_queryset()

    def get_queryset(self):
        return self.model.objects.all()

    def get_exportable(self):
        include = [c.label for c in self.get_api_arguments()["_include"]]
        exclude = [c.label for c in self.get_api_arguments()["_exclude"]]
        return self.get_exportable_class()(QuerySetTable, self.objects, include=include, exclude=exclude)

    def get_exportable_class(self) -> type(DeclaredTable):
        if self.exportable is None:
            return build_declared_table(self.model)
        return super().get_exportable_class()
