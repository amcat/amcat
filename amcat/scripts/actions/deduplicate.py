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

from django import forms
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
        ignore_title = forms.BooleanField(initial=False, required=False)
        ignore_byline = forms.BooleanField(initial=False, required=False)
        ignore_date = forms.BooleanField(initial=False, required=False)
        text_ratio = forms.IntegerField(required=False, initial=0, min_value=0, max_value=100,
                                        help_text="Percentage of (fuzzy) text overlap to be considered duplicate, e.g. 80")
        title_ratio = forms.IntegerField(required=False, initial=0, min_value=0, max_value=100,
                                            help_text="Percentage of (fuzzy) title overlap to be considered duplicate, e.g. 99")
        save_duplicates_to = forms.CharField(initial="", required=False, 
                                             help_text="If not empty, save duplicates to new set with this name.")

        dry_run = forms.BooleanField(initial=False, required=False)
        skip_simple = forms.BooleanField(initial=False, required=False, help_text="Do not use an approximation of levenhstein ratio using article length (if using fuzzy text or title")


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
            self._articles_cache = self._articles_cache.only("id", "text", "title")

        return self._articles_cache

    def _get_deduplicates(self, articleset_1, articleset_2, text_ratio, title_ratio, skip_simple, delete_same):
        log.warn("Start deduplicating ({articleset_1}, {articleset_2})..".format(**locals()))
        all_articles = articleset_1.articles.only("id", "date", "medium", "text", "title")
        n_articles = all_articles.count()
        articles = all_articles.order_by("medium", "date")

        for i, article in enumerate(articles.iterator(), start=1):
            if not i % 100 or i == n_articles:
                log.info("Checking article {i} of {n_articles}".format(**locals()))

            compare_with = self.get_articles(articleset_2, article, text_ratio)
            if not skip_simple:
                compare_with = self.get_simple_levenhstein(compare_with, article, text_ratio)
            compare_with = self.get_matching(compare_with, article, title_ratio, "title")
            compare_with = set(self.get_matching(compare_with, article, text_ratio, "text"))

            if not delete_same:
                discard = None
                for a in compare_with:
                    if a.id == article.id:
                        discard = a
                compare_with.discard(discard)

            if compare_with:
                yield (article, compare_with)

    def is_fuzzy_dupe(self, a, b):
        for field in 'title', 'text':
            ratio = self.options[field+'_ratio']
            if ratio:
                similarity =  Levenshtein.ratio(getattr(a, field), getattr(b, field))
                if similarity < (ratio / 100.):
                    return False
        return True
                
    def fuzzy_dedup(self, arts):
        """Do fuzzy deduplication on the given articles"""
        arts = sorted(arts, key=lambda a:a.id)
        while len(arts) > 1:
            a = arts.pop(0)
            dupes = [b for b in arts if self.is_fuzzy_dupe(a,b)]
            if dupes:
                arts = [a for a in arts if a not in dupes]
                yield a, dupes

    def get_fields(self, ignore_fuzzy=False):
        """
        Get the fields to retrieve/compare on.
        If ignore_fuzzy, ignore text if text_ratio is given
        """
        all_fields = ['medium', 'page', 'date', 'section', 'title', 'byline', 'text']
        if not (any(self.options['ignore_'+f] for f in all_fields) or
                (ignore_fuzzy and any(self.options.get(f+'_ratio') for f in all_fields))):
            yield 'hash'
        else:
            for f in all_fields:
                if self.options['ignore_'+f]: continue
                if ignore_fuzzy and self.options.get(f+'_ratio'): continue
                yield f

    def get_duplicates(self, date):
        fields = list(self.get_fields())
        compare_fields = list(self.get_fields(ignore_fuzzy=True))

        dupes = collections.defaultdict(set)
        for a in ES().query_all(filters={"sets": self.options['articleset'],
                                         "on_date": date}, fields=fields):
            key = tuple(getattr(a, f) for f in compare_fields)
            dupes[key].add(a)

        for arts in dupes.values():
            if len(arts) > 1:
                if self.options['title_ratio'] or self.options['text_ratio']:
                    for a, arts in self.fuzzy_dedup(arts):
                        yield a.id, [b.id for b in arts]
                else:
                    aids = sorted(a.id for a in arts)
                    yield aids[0], aids[1:]
                
    def _run(self, articleset, save_duplicates_to, dry_run, **kwargs):
        all_dupes = {}
        dupes_save_set = None
        log.debug("Deduplicating {articleset.id}".format(**locals()))
        for date in ES().list_dates(filters={"sets": articleset}):
            log.debug("Getting duplicates for {date}".format(**locals()))
            dupes = dict(self.get_duplicates(date))
            if dupes:
                all_dupes.update(dupes)
                todelete = list(itertools.chain(*dupes.values()))
                if not dry_run:
                    articleset.remove_articles(todelete)
                if save_duplicates_to:
                    if dupes_save_set is None:
                        dupes_save_set = ArticleSet.create_set(articleset.project, save_duplicates_to)
                    dupes_save_set.add_articles(todelete)

        log.debug("Deleted dupes for {} articles".format(len(all_dupes)))
        return all_dupes

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()

