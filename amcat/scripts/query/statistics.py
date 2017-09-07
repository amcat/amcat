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
import json
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from amcat.models import CodingValue, Code
from amcat.scripts.query import QueryAction
from amcat.tools.keywordsearch import SelectionSearch

from amcat.models.coding.codingschemafield import FIELDTYPE_IDS

log = logging.getLogger(__name__)


def get_used_codes(codingjobs):
    if not codingjobs:
        return Code.objects.none()

    codingjob_ids = [c.id for c in codingjobs]
    codingjob_filter = Q(coding__coded_article__codingjob__id__in=codingjob_ids)
    schemafield_filter = Q(field__fieldtype__id=FIELDTYPE_IDS.CODEBOOK)
    nonempty_filter = Q(intval__isnull=False)

    coding_values = CodingValue.objects.filter(codingjob_filter, schemafield_filter, nonempty_filter)
    codes = Code.objects.filter(id__in=coding_values.values_list("intval", flat=True))

    return codes

def get_used_code_ids(codingjobs):
    return get_used_codes(codingjobs).values_list("id", flat=True)


class StatisticsAction(QueryAction):
    """Statistics is a meta-action implemented allowing scripts to to query
    properties about the currently entered query. For example, it returns the
    included mediums, articlesets and terms for the current query. Note that
    it currently returns all mediums / articlesets as running the full query
    is yet to expensive.
    """
    output_types = (
        ("application/json+debug", "Inline"),
        ("application/json", "JSON"),
    )

    def run(self, form):
        selection = SelectionSearch(form)
        queries = selection.get_queries()
        articlesets = form.cleaned_data["articlesets"]
        codingjobs = form.cleaned_data["codingjobs"]

        statistics = selection.get_statistics()

        if hasattr(statistics, "start_date"):
            start_date = statistics.start_date
            end_date = statistics.end_date
        else:
            start_date = None
            end_date = None

        return json.dumps({
            "queries": {q.label: q.query for q in queries},
            "articlesets": {a.id: a.name for a in articlesets},
            "codingjobs": {cj.id: cj.name for cj in codingjobs},
            "codes_used": list(get_used_code_ids(codingjobs)),
            "statistics": {
                "start_date": start_date,
                "end_date": end_date,
                "narticles": statistics.n
            }
        }, cls=DjangoJSONEncoder)
