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
import re
from collections import defaultdict

from django.core.exceptions import ValidationError
from django.forms import ChoiceField, BooleanField

from amcat.models import ArticleSet, CodingJob, Label
from amcat.models import CodingSchemaField, Code, Coding
from amcat.models.coding.codingschemafield import FIELDTYPE_IDS
from amcat.scripts.forms.selection import get_all_schemafields
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.scripts.query.aggregation import AGGREGATION_FIELDS, get_aggregation_choices, \
    get_used_properties_by_articlesets
from amcat.scripts.query.queryaction import NotInCacheError
from amcat.tools import aggregate_orm
from amcat.tools.aggregate_orm import ORMAggregate
from amcat.tools.aggregate_orm.categories import POSTGRES_DATE_TRUNC_VALUES
from amcat.tools.keywordsearch import SelectionSearch, SearchQuery
from .aggregation import AggregationEncoder, aggregation_to_matrix, aggregation_to_csv

log = logging.getLogger(__name__)


CODINGSCHEMAFIELD_RE = re.compile("^codingschemafield\((?P<id>[0-9]+)\)$")
AVERAGE_CODINGSCHEMAFIELD_RE = re.compile("^avg\((?P<id>[0-9]+)\)$")



def get_schemafield_choices(codingjobs, values=True):
    schemafields = get_all_schemafields(codingjobs).order_by("label").only("id", "label")
    article_fields = schemafields.filter(codingschema__isarticleschema=True)
    sentence_fields = schemafields.filter(codingschema__isarticleschema=False)

    for src, fields in [("Article field", article_fields), ("Sentence field", sentence_fields)]:
        category_fields = list(get_category_fields(fields))
        if category_fields:
            yield src, category_fields

def get_category_fields(fields):
    for field in fields:
        if field.fieldtype_id  == FIELDTYPE_IDS.CODEBOOK:
            yield "codingschemafield(%s)" % field.id, field.label

def get_average_fields(fields):
    for field in fields:
        if field.fieldtype_id in (FIELDTYPE_IDS.INT, FIELDTYPE_IDS.QUALITY):
            yield "avg(%s)" % field.id, "Average %s" % field.label

def get_value_fields(fields):
    yield "Average", list(get_average_fields(fields))
    yield "Count", [
        ("count(articles)", "Number of articles"),
        ("count(codings)", "Number of codings"),
        ("count(codingvalues)", "Number of coding values")
    ]


class CodingAggregationActionForm(QueryActionForm):
    primary_use_codebook = BooleanField(initial=False, required=False, label="Group codings using codebook")
    primary = ChoiceField(choices=AGGREGATION_FIELDS, label="Aggregate on (primary)")
    primary_fill_zeroes = BooleanField(initial=True, required=False, label="Show empty dates as 0 (if interval selected)")

    secondary_use_codebook = BooleanField(initial=False, required=False, label="Group codings using codebook")
    secondary = ChoiceField(choices=(("", "------"),) + AGGREGATION_FIELDS, required=False, label="Aggregate on (secondary)")

    value1 = ChoiceField(label="First value", initial="count(articles)")
    value2 = ChoiceField(label="Second value", required=False, initial="")

    def __init__(self, *args, **kwargs):
        super(CodingAggregationActionForm, self).__init__(*args, **kwargs)

        assert self.codingjobs
        assert self.schemafields is not None

        value_choices = tuple(get_value_fields(self.schemafields))
        self.fields["value1"].choices = value_choices
        self.fields["value2"].choices = (("", "------"),) + value_choices

        sets = {cj.articleset for cj in self.codingjobs}
        props = set(get_used_properties_by_articlesets(sets))
        self.prop_choices = (*get_aggregation_choices(props),)
        self.meta_choices = (("Metadata Fields", (("year", "Year"), ("month", "Month"), ("week", "Week"))),)
        schema_choices = tuple(get_schemafield_choices(self.codingjobs))


        self.fields["primary"].choices += schema_choices + self.prop_choices + self.meta_choices
        self.fields["secondary"].choices += schema_choices + self.prop_choices + self.meta_choices

        project_codebooks = self.project.get_codebooks()

    def _clean_aggregation(self, field_name, prefix=None):
        field_value = self.cleaned_data[field_name]
        if not field_value:
            return None

        if field_value in POSTGRES_DATE_TRUNC_VALUES:
            return aggregate_orm.IntervalCategory(interval=field_value, prefix=prefix, is_json_field=False)

        if field_value == "articleset":
            return aggregate_orm.ArticleSetCategory(prefix=prefix)

        if field_value == "term":
            return aggregate_orm.TermCategory()

        if field_value in [k for k, v in self.prop_choices[0][1]]:
            if field_value.endswith("_str"):
                # _str is added to disambiguate between fields and intervals (why, though?!)
                field_value, _ = field_value.rsplit("_", 1)
            use_codebook = self.cleaned_data["{}_use_codebook".format(field_name)]
            kwargs = {}
            if use_codebook:
                codebook = self.cleaned_data['codebook']
                lang = self.cleaned_data['codebook_label_language']
                groups = defaultdict(list)
                for code, p in codebook.get_hierarchy():
                    if p is None:
                        p = code
                    try:
                        groups[p.get_label(lang)].append(code.get_label(lang))
                    except Label.DoesNotExist:
                        pass
                kwargs['groupings'] = groups
            return aggregate_orm.ArticleFieldCategory(True, field_value, **kwargs)

        # Test for schemafield
        match = CODINGSCHEMAFIELD_RE.match(field_value)
        if match:
            codingschemafield_id = int(match.groupdict()["id"])
            codingschemafield = CodingSchemaField.objects.get(id=codingschemafield_id)
            use_codebook = self.cleaned_data["{}_use_codebook".format(field_name)]
            codebook = codingschemafield.codebook if use_codebook else None
            return aggregate_orm.SchemafieldCategory(codingschemafield, codebook=codebook, prefix=prefix)
        raise ValidationError("Not a valid aggregation: %s." % field_value)

    def clean_primary(self):
        return self._clean_aggregation("primary", prefix="1")

    def clean_secondary(self):
        return self._clean_aggregation("secondary", prefix="3")

    def _clean_value(self, field_name, prefix=None):
        field_value = self.cleaned_data[field_name]

        if not field_value:
            return None

        if field_value == "count(articles)":
            return aggregate_orm.CountArticlesValue(prefix=prefix)

        if field_value == "count(codings)":
            return aggregate_orm.CountCodingsValue(prefix=prefix)

        if field_value == "count(codingvalues)":
            return aggregate_orm.CountCodingValuesValue(prefix=prefix)

        match = AVERAGE_CODINGSCHEMAFIELD_RE.match(field_value)
        if match:
            codingschemafield_id = int(match.groupdict()["id"])
            codingschemafield = CodingSchemaField.objects.get(id=codingschemafield_id)
            return aggregate_orm.AverageValue(codingschemafield, prefix=prefix)

        raise ValidationError("Not a valid value: %s." % field_value)

    def clean_value1(self):
        return self._clean_value("value1", prefix="2")

    def clean_value2(self):
        return self._clean_value("value2", prefix="4")

    def clean(self):
        if self._errors:
            return
        output_type = self.cleaned_data["output_type"]
        primary = self.cleaned_data["primary"]
        secondary = self.cleaned_data["secondary"]
        value2 = self.cleaned_data["value2"]

        if primary and secondary and value2 and output_type != "text/json+aggregation+table":
            error_msg = "When selecting two aggregations (primary and secondary), " \
                        "you can only select one value."
            raise ValidationError(error_msg)

        return self.cleaned_data

def to_sortable_tuple(key):
    if isinstance(key, tuple):
        return tuple(map(to_sortable_tuple, key))
    elif isinstance(key, (ArticleSet, CodingJob)):
        return key.name.lower()
    elif isinstance(key, (Code, SearchQuery)):
        return key.label.lower()
    return key


class CodingAggregationAction(QueryAction):
    output_types = (
        ("text/json+aggregation+barplot", "Bar plot"),
        ("text/json+aggregation+table", "Table"),
        ("text/json+aggregation+scatter", "Scatter plot"),
        ("text/json+aggregation+line", "Line plot"),
        ("text/json+aggregation+heatmap", "Heatmap"),
        ("text/csv", "CSV (Download)"),
    )
    form_class = CodingAggregationActionForm


    def run(self, form):
        self.monitor.update(1, "Executing query..")
        selection = SelectionSearch.get_instance(form)
        try:
            aggregation, primary, secondary, categories, values = self.get_cache()
        except NotInCacheError:
            narticles = selection.get_count()
            self.monitor.update(10, "Found {narticles} articles. Aggregating..".format(**locals()))

            # Get aggregation
            codingjobs = form.cleaned_data["codingjobs"]
            primary = form.cleaned_data['primary']
            secondary = form.cleaned_data['secondary']
            value1 = form.cleaned_data['value1']
            value2 = form.cleaned_data['value2']

            article_ids = list(selection.get_article_ids())

            codings = Coding.objects.filter(coded_article__article__id__in=article_ids,
                                            coded_article__codingjob__id__in=selection.data.codingjobs)

            terms = selection.get_article_ids_per_query()
            orm_aggregate = ORMAggregate(codings, flat=False, terms=terms)
            categories = list(filter(None, [primary, secondary]))
            values = list(filter(None, [value1, value2]))
            aggregation = orm_aggregate.get_aggregate(categories, values)
            aggregation = sorted(aggregation, key=to_sortable_tuple)

            self.set_cache([aggregation, primary, secondary, categories, values])
        else:
            self.monitor.update(10, "Found in cache. Rendering..".format(**locals()))

        if form.cleaned_data.get("primary_fill_zeroes") and hasattr(primary, 'interval'):
            # aggregate_es does not have fill zeroes - does js handle that?
            pass#aggregation = list(aggregate_es.fill_zeroes(aggregation, primary, secondary))
        # Matrices are very annoying to construct in javascript due to missing hashtables. If
        # the user requests a table, we thus first convert it to a different format which should
        # be easier to render.
        if form.cleaned_data["output_type"] == "text/json+aggregation+table":
            aggregation = aggregation_to_matrix(aggregation, categories)

        if form.cleaned_data["output_type"] == "text/csv":
            return aggregation_to_csv(aggregation, categories, values)

        self.monitor.update(60, "Serialising..".format(**locals()))
        return json.dumps(aggregation, cls=AggregationEncoder, check_circular=False)


class AggregationColumnAction(QueryAction):
    pass
