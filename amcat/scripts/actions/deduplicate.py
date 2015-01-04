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
from django.core.exceptions import ValidationError
from amcat.scripts.script import Script

from amcat.models import ArticleSet
from amcat.tools.amcates import ES

import Levenshtein

class Deduplicate(Script):
    """
    Deduplicate articles using two articlesets. For all duplicated articles the articles in
    set 2 will be removed. If you want to deduplicate one articleset, use it as both
    articleset 1 and articleset 2 and make sure to *uncheck* 'delete same'. Dry run invokes
    a test run which doesn't touch any data.

    Differences are calculated using [Levenshtein distances](https://en.wikipedia.org/wiki/Levenshtein_distance).
    A very simple algorithm based on article length is used to narrow the datasets Levenshtein
    has to consider. This speeds up the process significantly, but might incur some inaccuracy. To
    disable this bahaviour use 'skip simple'.
    """

    def __init__(self, *args, **kwargs):
        super(Deduplicate, self).__init__(*args, **kwargs)
        self._articles_cache_contains = None
        self._articles_cache = None

    class options_form(forms.Form):
        articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())

        ignore_medium = forms.BooleanField(initial=False, required=False)
        ignore_page = forms.BooleanField(initial=False, required=False)
        ignore_text = forms.BooleanField(initial=False, required=False)
        ignore_section = forms.BooleanField(initial=False, required=False)
        ignore_headline = forms.BooleanField(initial=False, required=False)
        ignore_byline = forms.BooleanField(initial=False, required=False)
        ignore_date = forms.BooleanField(initial=False, required=False)
        
        text_ratio = forms.IntegerField(required=False, initial=0, min_value=0, max_value=100,
                                        help_text="Percentage of (fuzzy) text overlap to be considered duplicate, e.g. 80")
        headline_ratio = forms.IntegerField(required=False, initial=0, min_value=0, max_value=100,
                                            help_text="Percentage of (fuzzy) headline overlap to be considered duplicate, e.g. 99")

        dry_run = forms.BooleanField(initial=False, required=False)
        skip_simple = forms.BooleanField(initial=False, required=False, help_text="Do not use an approximation of levenhstein ratio using article length (if using fuzzy text or headline")


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

            if not delete_same:
                discard = None
                for a in compare_with:
                    if a.id == article.id:
                        discard = a
                compare_with.discard(discard)

            if compare_with:
                yield (article, compare_with)

    def get_fields(self):
        all_fields = ['medium', 'page', 'date', 'section', 'headline', 'byline', 'text']
        if not any(self.options['ignore_'+f] for f in all_fields):
            return ['hash']

        return [f for f in all_fields
                if not self.options['ignore_'+f]]
        
    def get_duplicates(self, date):
        fields = list(self.get_fields())
        dupes = collections.defaultdict(set)
        for a in ES().query_all(filters={"sets": self.options['articleset'],
                                         "on_date": date}, fields=fields):
            key = tuple(getattr(a, f) for f in fields)
            dupes[key].add(a.id)

        for aids in dupes.values():
            if len(aids) > 1:
                for aid in sorted(aids)[1:]:
                    yield aid
                
    def _run(self, articleset, dry_run, **kwargs):
        nn = 0
        for date in ES().list_dates(filters={"sets": articleset}):
            log.info("Getting duplicates for {date}".format(**locals()))
            dupes = list(self.get_duplicates(date))
            if dupes:
                log.info("Deleting duplicates: {dupes}".format(**locals()))
                nn += len(dupes)
                if not dry_run:
                    articleset.remove_articles(dupes)
        log.info("Deleted {nn} dupes".format(**locals()))
        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestDedup(amcattest.AmCATTestCase):
        

    def do_test(self, articles, **options):
        s = amcattest.create_test_set(articles=articles)
        ES().flush()
        Deduplicate(articleset=s.id, **options).run()
        ES().flush()
        return sorted(s.articles.values_list("pk", flat=True))
        
        
    def test_fields(self):
        s = amcattest.create_test_set()
        self.assertEqual(set(Deduplicate(articleset=s.id).get_fields()), {'hash'})
        self.assertEqual(set(Deduplicate(articleset=s.id, ignore_medium=True).get_fields()),
                         {'text', 'headline', 'byline', 'section', 'page', 'date'})
    
    @amcattest.use_elastic
    def test_dedup(self):
        s = amcattest.create_test_set()
        m1, m2 = [amcattest.create_test_medium() for _x in range(2)]
        arts = [
            amcattest.create_test_article(articleset=s, medium=m1, pagenr=1),
            amcattest.create_test_article(articleset=s, medium=m1, pagenr=2),
            amcattest.create_test_article(articleset=s, medium=m2, pagenr=1),
            amcattest.create_test_article(articleset=s, medium=m2, pagenr=2),
            amcattest.create_test_article(articleset=s, medium=m2, pagenr=2)
            ]
        aids = [a.id for a in arts]
        self.assertEqual(self.do_test(arts), aids[:4])
        self.assertEqual(self.do_test(arts, dry_run=True), aids)
        self.assertEqual(self.do_test(arts, ignore_medium=True), aids[:2])
        self.assertEqual(self.do_test(arts, ignore_page=True), [aids[0], aids[2]])

    @amcattest.use_elastic
    def test_date(self):
        s = amcattest.create_test_set()
        m = amcattest.create_test_medium()
        arts = [
            amcattest.create_test_article(articleset=s, medium=m, date="2001-01-01"),
            amcattest.create_test_article(articleset=s, medium=m, date="2001-01-01 02:00"),
            amcattest.create_test_article(articleset=s, medium=m, date="2001-01-02"),
            ]
        aids = [a.id for a in arts]

        self.assertEqual(self.do_test(arts), aids)
        self.assertEqual(self.do_test(arts, ignore_date=True), [aids[0], aids[2]])
