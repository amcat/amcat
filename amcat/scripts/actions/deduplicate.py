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

    class options_form(forms.Form):
        articleset_1 = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
        articleset_2 = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
        dry_run = forms.BooleanField(initial=False, required=False)
        text_ratio = forms.IntegerField(initial=99, help_text="Match articles which text match ..%%")
        headline_ratio = forms.IntegerField(initial=80, help_text="Compare articles which headlines match ..%%")
        keep_same = forms.BooleanField(initial=False, required=False, help_text=r"Never remove articles with same id's")

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
        
    def _get_deduplicates(self, articleset_1, articleset_2, text_ratio, headline_ratio, keep_same):
        # Very naive implementation. Results in many many queries.
        log.info("Start deduplicating ({articleset_1}, {articleset_2})..".format(**locals()))

        # Keep a mapping of duplicates.
        duplicates = {}
        n_articles = articleset_1.articles.count()
        for i, article in enumerate(articleset_1.articles.only("id", "date", "medium", "text", "headline").iterator(), start=1):
            if not i % 100 or i == n_articles:
                log.info("Checking article {i} of {n_articles}".format(**locals()))

            compare_with = articleset_2.articles.filter(date=article.date, medium__id=article.medium_id)
            compare_with = compare_with.only("id", "text", "headline")
            compare_with = self.get_matching(compare_with, article, headline_ratio, "headline")
            compare_with = set(self.get_matching(compare_with, article, text_ratio, "text"))

            if not keep_same:
                compare_with -= {article,}

            if compare_with:
                yield(article, compare_with)

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

