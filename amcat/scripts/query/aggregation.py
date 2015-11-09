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
from __future__ import unicode_literals

import json
from datetime import datetime
from time import mktime

from django.core.exceptions import ValidationError
from django.forms import ChoiceField

from amcat.models import Medium, ArticleSet, CodingSchemaField, Code, CodingJob
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools import aggregate_es
from amcat.tools.aggregate_es.categories import ELASTIC_TIME_UNITS
from amcat.tools.keywordsearch import SelectionSearch, SearchQuery


AGGREGATION_FIELDS = (
    ("articleset", "Articleset"),
    ("medium", "Medium"),
    ("term", "Term"),
    ("Interval", (
        ("year", "Year"),
        ("quarter", "Quarter"),
        ("month", "Month"),
        ("week", "Week"),
        ("day", "Day")
    ))
)


class AggregationEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return int(mktime(obj.timetuple())) * 1000
        if isinstance(obj, (Medium, ArticleSet, CodingJob)):
            return {"id": obj.id, "label": obj.name}
        if isinstance(obj, SearchQuery):
            return {"id": obj.label, "label": obj.query}
        if isinstance(obj, (CodingSchemaField, Code)):
            return {"id": obj.id, "label": obj.label}
        return super(AggregationEncoder, self).default(obj)


MEDIUM_ERR = "Could not find medium with id={column} or name={column}"

class AggregationActionForm(QueryActionForm):
    primary = ChoiceField(label="Primary aggregation", choices=AGGREGATION_FIELDS)
    secondary = ChoiceField(label="Secondary aggregation", choices=(("", "------"),) + AGGREGATION_FIELDS, required=False)

    #relative_to = CharField(widget=Select, required=False)

    def __init__(self, *args, **kwargs):
        super(AggregationActionForm, self).__init__(*args, **kwargs)
        assert not self.codingjobs

    def _clean_aggregation(self, field_name):
        field_value = self.cleaned_data[field_name]

        if not field_value:
            return None

        if field_value in ELASTIC_TIME_UNITS:
            return aggregate_es.IntervalCategory(field_value)

        if field_value == "medium":
            return aggregate_es.MediumCategory()

        if field_value == "articleset":
            return aggregate_es.ArticlesetCategory(self.articlesets)

        if field_value == "term":
            terms = SelectionSearch(self).get_queries()
            return aggregate_es.TermCategory(terms)

        raise ValidationError("Not a valid value: %s" % field_value)

    def clean_primary(self):
        return self._clean_aggregation("primary")

    def clean_secondary(self):
        return self._clean_aggregation("secondary")


class AggregationAction(QueryAction):
    """
    Aggregate articles based on their properties. Make sure x_axis != y_axis.
    """
    output_types = (
        ("text/json+aggregation+barplot", "Bar plot"),
        ("text/json+aggregation+table", "Table"),
        ("text/json+aggregation+scatter", "Scatter plot"),
        ("text/json+aggregation+line", "Line plot"),
        ("text/json+aggregation+heatmap", "Heatmap"),
        ("text/csv", "CSV (Download)"),
    )
    form_class = AggregationActionForm

    def run(self, form):
        self.monitor.update(1, "Executing query..")
        selection = SelectionSearch(form)
        narticles = selection.get_count()
        self.monitor.update(10, "Found {narticles} articles. Aggregating..".format(**locals()))

        # Get aggregation
        primary = form.cleaned_data["primary"]
        secondary= form.cleaned_data["secondary"]
        categories = list(filter(None, [primary, secondary]))
        aggregation = selection.get_aggregate(categories, flat=False)

        self.monitor.update(60, "Serialising..".format(**locals()))
        return json.dumps(list(aggregation), cls=AggregationEncoder, check_circular=False)
