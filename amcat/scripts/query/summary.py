##########################################################################
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

import datetime
import json
import re

from django import forms
from django.forms import IntegerField, BooleanField, ChoiceField
from django.template import Context
from django.template.loader import get_template
from typing import Sequence

from amcat.forms.forms import order_fields
from amcat.models import Article, get_used_properties_by_articlesets
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools import toolkit
from amcat.tools.aggregate_es import IntervalCategory
from amcat.tools.amcates import ARTICLE_FIELDS
from amcat.tools.amcates_queryset import ESQuerySet
from amcat.tools.keywordsearch import SelectionSearch
from amcat.tools.toolkit import Timer

TEMPLATE = get_template('query/summary/summary.html')

TIMEDELTAS = [
    ("day", datetime.timedelta(1)),
    ("week", datetime.timedelta(7)),
    ("month", datetime.timedelta(30)),
    ("quarter", datetime.timedelta(120)),
    ("year", datetime.timedelta(365)),
]

MAX_DATE_GROUPS = 500


def get_fragments(query: str, article_ids: Sequence[int], fragment_size=150, number_of_fragments=3):
    order_to_keep = article_ids

    if not query:
        query = toolkit.random_alphanum(20)

    articles = Article.objects.defer("text", "title").in_bulk(article_ids)
    qs = ESQuerySet().filter(id__in=article_ids)
    fragments = qs.highlight_fragments(query, ("text", "title"), mark="em", fragment_size=fragment_size, number_of_fragments=number_of_fragments)
    for article_id, fields in fragments.items():
        
        if number_of_fragments == 0:
            articles[article_id].text = ""
            continue

        articles[article_id]._highlighted = True  # Disable save()
        for field, highlights in fields.items():
            if len(highlights) > 1:
                fragment = "<p>... " + " ...</p><p>... ".join(h.strip().replace("\n", " ") for h in highlights) + " ...</p>"
            else:
                fragment = highlights[0]
            setattr(articles[article_id], field, fragment)
    return [articles[id] for id in order_to_keep]

@order_fields(("offset", "size", "number_of_fragments", "fragment_size", "show_fields"))
class SummaryActionForm(QueryActionForm):
    size = IntegerField(initial=40)
    offset = IntegerField(initial=0)
    number_of_fragments = IntegerField(initial=3)
    fragment_size = IntegerField(initial=150)
    show_fields = forms.MultipleChoiceField(choices=(), initial=(), required=False)
    aggregations = BooleanField(initial=True, required=False)

    sort_by = ChoiceField(choices=(("", "---"), ("date", "Date")), initial="date", required=False)
    sort_descending = BooleanField(initial=True, required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

        article_props = set(get_used_properties_by_articlesets(self.articlesets))
        self.fields["show_fields"].choices = sorted((p, p) for p in article_props)
        self.fields["show_fields"].initial = [p for p in ("author", "publisher", "section") if p in article_props]


class SummaryAction(QueryAction):
    output_types = (("text/html+summary", "HTML"),)
    form_class = SummaryActionForm
    monitor_steps = 4

    def get_highlighted_article_fragments(self):
        pass

    def run(self, form):
        form_data = dict(form.data.lists())
        for value in form_data.values():
            if value == [None]:
                value.pop()
        form_data = json.dumps(form_data, indent=4)

        size = form.cleaned_data['size']
        offset = form.cleaned_data['offset']
        number_of_fragments = form.cleaned_data['number_of_fragments']
        fragment_size = form.cleaned_data['fragment_size']
        show_fields = sorted(form.cleaned_data['show_fields'])
        show_aggregation = form.cleaned_data['aggregations']
        sort_by = form.cleaned_data.get('sort_by')
        sort_desc = "desc" if form.cleaned_data.get('sort_descending', False) else "asc"

        if sort_by:
            sort = [":".join([sort_by, sort_desc])]
        else:
            sort = []

        with Timer() as timer:
            selection = SelectionSearch.get_instance(form)
            self.monitor.update(message="Executing query..")
            narticles = selection.get_count()
            self.monitor.update(message="Fetching articles..".format(**locals()))
            articles = selection.get_articles(size=size, offset=offset, sort=sort).as_dicts()
            articles = get_fragments(selection.get_query(), [a["id"] for a in articles], fragment_size, number_of_fragments)

            if show_aggregation:
                self.monitor.update(message="Aggregating..".format(**locals()))
                
                statistics = selection.get_statistics()
                try:
                    delta_start_end = statistics.end_date - statistics.start_date
                    interval = next(interval for (interval, delta) in TIMEDELTAS
                                    if MAX_DATE_GROUPS * delta > delta_start_end)
                except (StopIteration, TypeError):
                    interval = "day"

                date_aggr = selection.get_aggregate([IntervalCategory(interval)], objects=False)
            else:
                # Increase progress without doing anything (because we don't have to aggregate)
                self.monitor.update()

            self.monitor.update(message="Rendering results..".format(**locals()))

        return TEMPLATE.render(Context(dict(locals(), **{
            "project": self.project, "user": self.user
        })))

