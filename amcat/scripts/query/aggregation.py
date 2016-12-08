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
import logging
import io

from typing import Iterable, Tuple

from amcat.scripts.query.queryaction import NotInCacheError
from amcat.tools import amcates
from amcat.tools.amcates import get_property_primitive_type, ARTICLE_FIELDS


import csv
import json
import datetime
from itertools import chain, repeat

from django.core.exceptions import ValidationError
from django.forms import ChoiceField, BooleanField

from amcat.models import ArticleSet, CodingSchemaField, Code, CodingJob
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools import aggregate_es
from amcat.tools.aggregate_es.categories import ELASTIC_TIME_UNITS, IntervalCategory, FieldCategory
from amcat.tools.aggregate_orm import CountArticlesValue
from amcat.tools.keywordsearch import SelectionSearch, SearchQuery, to_sortable_tuple

log = logging.getLogger(__name__)

AGGREGATION_FIELDS = (
    ("articleset", "Articleset"),
    ("term", "Term"),
)

EMPTY_MATRIX = {
    "rows": (),
    "columns": (),
    "data": ()
}

def aggregation_to_matrix(aggregation, categories):
    """
    Converts an aggregation of the form [(categories, values)] to a matrix represented by
    a matrix with the keys 'columns', 'rows', and 'data'. The result is guaranteed to be
    sorted.

    @param aggregation: aggregation from either ES or ORM backend
    @param categories: list of instances of Category
    @return: matrix / dict
    """
    if not aggregation:
        return dict(EMPTY_MATRIX)

    # No real "columns" exist if only one category is selected
    if len(categories) == 1:
        return {
            "columns": ["Value"],
            "rows": [cats[0] for cats, vals in aggregation],
            "data": [(vals,) for cats, vals in aggregation]
        }

    if len(categories) > 2:
        raise ValueError("More than two categories not yet supported by aggregation_to_matrix()")

    # Two categories, plus an arbitrary number of values.
    rows = sorted({cats[0] for cats, vals in aggregation}, key=to_sortable_tuple)
    cols = sorted({cats[1] for cats, vals in aggregation}, key=to_sortable_tuple)

    row_positions = {r: n for n, r in enumerate(rows)}
    col_positions = {c: n for n, c in enumerate(cols)}

    matrix = [[(None,)]*len(cols) for _ in range(len(rows))]
    for (row, col), values in aggregation:
        matrix[row_positions[row]][col_positions[col]] = values

    return {
        "data": matrix,
        "rows": rows,
        "columns": cols
    }

def aggregation_to_csv(aggregation, categories, values):
    aggregation = map(chain.from_iterable, aggregation)

    csvio = io.StringIO()
    csvf = csv.writer(csvio)

    catvals = repeat(list(chain(categories, values)))
    header = chain.from_iterable(c.get_column_names() for c in next(catvals))
    csvf.writerow(list(header))

    for catval, row in zip(catvals, aggregation):
        values = (c.get_column_values(obj) for obj, c in zip(row, catval))
        csvf.writerow(list(chain.from_iterable(values)))

    return csvio.getvalue()


class AggregationEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, (ArticleSet, CodingJob)):
            return {"id": obj.id, "label": obj.name}
        if isinstance(obj, SearchQuery):
            return {"id": obj.label, "label": obj.query}
        if isinstance(obj, (CodingSchemaField, Code)):
            return {"id": obj.id, "label": obj.label}
        return super(AggregationEncoder, self).default(obj)


HUMAN_READABLE_TYPES = {
    str: "string",
    int: "integer",
    float: "number"
}

INTERVALS = (
    "year",
    "quarter",
    "month",
    "week",
    "day"
)


def get_property_basename(property):
    if "_" in property:
        return property[:property.find("_")]
    return property


def get_aggregation_choice(property: str) -> Tuple:
    basename = get_property_basename(property)
    ptype = get_property_primitive_type(property)

    if ptype is str:
        return (property + "_str", basename)
    elif ptype in (int, float):
        value = "{}_{}".format(property, ptype.__name__)
        label = "{} ({})".format(basename, HUMAN_READABLE_TYPES[ptype])
        return (value, label)
    elif ptype is datetime.datetime:
        return ("{} (date)".format(basename), (
            ("{}_year".format(property), "Year"),
            ("{}_quarter".format(property), "Quarter"),
            ("{}_month".format(property), "Month"),
            ("{}_week".format(property), "Week"),
            ("{}_day".format(property), "Day")
        ))
    else:
        raise ValueError("Primitive type {} not recognized".format(ptype))


def get_aggregation_choices(properties: Iterable[str]) -> Iterable[Tuple]:
    choices = list(map(get_aggregation_choice, properties))
    normal_choices = sorted(c for c in choices if not c[0].endswith(" (date)"))
    date_choices = sorted(c for c in choices if c[0].endswith(" (date)"))
    return (("Article fields", tuple(normal_choices)),) + tuple(date_choices)


class AggregationActionForm(QueryActionForm):
    primary = ChoiceField(label="Primary aggregation", choices=())
    secondary = ChoiceField(label="Secondary aggregation", choices=(), required=False)

    value1 = ChoiceField(label="First value", initial="count(articles)", choices=[("count(articles)", "Article count")])
    value2 = ChoiceField(label="Second value", required=False, initial="", choices=())

    fill_zeroes = BooleanField(label="Show empty dates as 0 (if interval selected)", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(AggregationActionForm, self).__init__(*args, **kwargs)
        assert not self.codingjobs

        properties = set()
        for articleset in self.articlesets:
            properties |= articleset.get_used_properties()
        properties |= ARTICLE_FIELDS - {"parent_hash"}
        aggregation_choices = (("Meta fields", AGGREGATION_FIELDS),) + tuple(get_aggregation_choices(properties))

        self.fields["primary"].choices = aggregation_choices
        self.fields["secondary"].choices = (("", "------"),) + aggregation_choices

    def _clean_aggregation(self, field_name):
        field_value = self.cleaned_data[field_name]

        if not field_value:
            return None

        if field_value == "articleset":
            return aggregate_es.ArticlesetCategory(self.articlesets)

        if field_value == "term":
            terms = SelectionSearch(self).get_queries()
            return aggregate_es.TermCategory(terms)

        if field_value.endswith(INTERVALS):
            fieldname, interval = field_value.rsplit("_", 1)
            return aggregate_es.IntervalCategory(field=fieldname, interval=interval)

        if field_value.endswith("_str"):
            # _str is added to disambiguate between fields and intervals
            field_value, _ = field_value.rsplit("_", 1)

        return FieldCategory.from_fieldname(field_value)

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
    monitor_steps = 4

    def run(self, form):
        selection = SelectionSearch(form)

        try:
            # Try to retrieve cache values
            primary, secondary, categories, aggregation = self.get_cache()
        except NotInCacheError:
            self.monitor.update(message="Executing query..")
            narticles = selection.get_count()
            self.monitor.update(message="Found {narticles} articles. Aggregating..".format(**locals()))

            # Get aggregation
            primary = form.cleaned_data["primary"]
            secondary= form.cleaned_data["secondary"]
            categories = list(filter(None, [primary, secondary]))
            aggregation = list(selection.get_aggregate(categories, flat=False))

            self.set_cache([primary, secondary, categories, aggregation])
        else:
            self.monitor.update(2)

        if form.cleaned_data.get("fill_zeroes") and type(primary) is IntervalCategory:
            self.monitor.update(message="Filling zeroes..")
            aggregation = list(aggregate_es.fill_zeroes(aggregation, primary, secondary))
        else:
            self.monitor.update()


        # Matrices are very annoying to construct in javascript due to missing hashtables. If
        # the user requests a table, we thus first convert it to a different format which should
        # be easier to render.
        if form.cleaned_data["output_type"] == "text/json+aggregation+table":
            aggregation = aggregation_to_matrix(aggregation, categories)

        if form.cleaned_data["output_type"] == "text/csv":
            return aggregation_to_csv(aggregation, categories, [CountArticlesValue()])

        self.monitor.update(message="Serialising..".format(**locals()))
        return json.dumps(aggregation, cls=AggregationEncoder, check_circular=False)
