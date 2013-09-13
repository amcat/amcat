#!/usr/bin/python

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

import logging; log = logging.getLogger(__name__)

import collections
import itertools
import pprint

from django import forms
from django.forms import widgets
from django.core.exceptions import ValidationError
from amcat.scripts.script import Script

from amcat.models import ArticleSet

try:
    import Levenshtein
except ImportError:
    Levenshtein = None
    log.error("Levenshtein module not installed. Deduplicate cannot be used.")

class Deduplicate(Script):
    """
    Deduplicate articles using two articlesets. For all duplicated articles
    the articles in set 2 will be removed. 
    """
    def __init__(self, *args, **kwargs):
        super(Deduplicate, self).__init__(*args, **kwargs)
        self._articles_cache_contains = None
        self._articles_cache = None

    class options_form(forms.Form):
        articleset_1 = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
        articleset_2 = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
        dry_run = forms.BooleanField(initial=False, required=False)
        text_ratio = forms.IntegerField(initial=99, help_text="Match articles which text match ..%%")
        headline_ratio = forms.IntegerField(initial=80, help_text="Compare articles which headlines match ..%%")
        delete_same = forms.BooleanField(initial=False, required=False, help_text="Remove articles with same id's")
        skip_simple = forms.BooleanField(initial=False, required=False, help_text="Do not use an approximation of levenhstein ratio")

        def clean_ratio(self, ratio):
            if not (0 <= self.cleaned_data[ratio] <= 100):
                raise ValidationError("{}: give a percentage. For example: 20.".format(ratio))
            return self.cleaned_data[ratio] / 100.0

        def clean_text_ratio(self):
            return self.clean_ratio("text_ratio")

        def clean_headline_ratio(self):
            return self.clean_ratio("headline_ratio")

    def get_matching(self, compare_with, article, ratio, prop):
        return (ca for ca in compare_with if Levenshtein.ratio(
                    getattr(article, prop), getattr(ca, prop)) >= ratio)

    def get_simple_levenhstein(self, articles, article, text_ratio):
        text_length = len(article.text)
        min_length = text_ratio * text_length
        max_length = ((1 - text_ratio) + 1) * text_length

        for comp_article in articles:
            if min_length <= len(comp_article.text) <= max_length:
                yield comp_article

    def get_articles(self, articleset, article, text_ratio):
        medium_id, date = article.medium_id, article.date

        # Same medium / date since previous call?
        if not self._articles_cache_contains == (medium_id, date):
            # Fill cache
            self._articles_cache_contains = (medium_id, date)
            self._articles_cache = articleset.articles.filter(date=date, medium__id=medium_id)
            self._articles_cache = self._articles_cache.only("id", "text", "headline")

        return self._articles_cache

    def _get_deduplicates(self, articleset_1, articleset_2, text_ratio, headline_ratio, skip_simple, delete_same):
        log.info("Start deduplicating ({articleset_1}, {articleset_2})..".format(**locals()))
        all_articles = articleset_1.articles.only("id", "date", "medium", "text", "headline")
        n_articles = all_articles.count()
        articles = all_articles.order_by("medium", "date")

        for i, article in enumerate(articles.iterator(), start=1):
            if not i % 100 or i == n_articles:
                log.info("Checking article {i} of {n_articles}".format(**locals()))

            compare_with = self.get_articles(articleset_2, article, text_ratio)
            if not skip_simple:
                compare_with = self.get_simple_levenhstein(compare_with, article, text_ratio)
            compare_with = self.get_matching(compare_with, article, headline_ratio, "headline")
            compare_with = set(self.get_matching(compare_with, article, text_ratio, "text"))

            print(compare_with)
            if not delete_same:
                discard = None
                for a in compare_with:
                    if a.id == article.id:
                        discard = a
                compare_with.discard(discard)
            print(compare_with)

            if compare_with:
                yield (article, compare_with)

    def _run(self, dry_run, articleset_2, **kwargs):
        duplicates = collections.defaultdict(list)

        for art, dupes in self._get_deduplicates(articleset_2=articleset_2, **kwargs):
            for dupe in dupes:
                duplicates[art].append(dupe)
            
        if not dry_run:
            articleset_2.articles.through.objects.filter(articleset=articleset_2,
                article__in=itertools.chain.from_iterable(duplicates.values())
            ).delete()
        else:
            pprint.pprint(dict(duplicates))

        return duplicates


if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()

