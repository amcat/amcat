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
from collections import OrderedDict
import json
from django.core.paginator import Paginator, Page, InvalidPage

from rest_framework import pagination
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from api.rest import count


def get_echo(request):
    opts = request.GET.get("datatables_options")

    try:
        opts = json.loads(opts)
    except (TypeError, ValueError) as e:
        return None
    else:
        return opts.get('sEcho')


class AmCATPaginator(Paginator):
    def _get_page(self, *args, **kwargs):
        return AmCATPage(*args, **kwargs)


class AmCATPage(Page):
    def __iter__(self):
        if hasattr(self.object_list, "iterator"):
            # If possible, return a Django iterator which, if the database supports it,
            # scrolls through the results instead of fetching them all at once.
            return self.object_list.iterator()
        return iter(super())

    def __len__(self):
        return count.count(self.object_list)


# Warning: this code has been monkey-patched, see below
class AmCATPageNumberPagination(pagination.PageNumberPagination):
    page_size = 10
    max_page_size = 100000
    page_size_query_param = "page_size"

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        self._handle_backwards_compat(view)

        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = AmCATPaginator(queryset, page_size) # <--- MONKEY PATCHED
        page_number = request.query_params.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=str(exc)
            )
            raise NotFound(msg)

        if paginator.count > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return self.page

    def get_paginated_response(self, data):
        headers = {
            'X-REST-ECHO': get_echo(self.request) or "",
            'X-REST-TOTAL': self.page.paginator.count,
            'X-REST-PER-PAGE': self.page.paginator.per_page,
            'X-REST-PAGES': self.page.paginator.num_pages,
            'X-REST-PAGE': self.page.number,
        }

        return Response(headers=headers, data=OrderedDict([
            ('echo', get_echo(self.request)),
            ('total', self.page.paginator.count),
            ('per_page', self.page.paginator.per_page),
            ('pages', self.page.paginator.num_pages),
            ('page', self.page.number),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))

