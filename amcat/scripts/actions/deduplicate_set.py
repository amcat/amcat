
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

import collections
import logging
from itertools import chain
from typing import Iterable, Tuple
from hashlib import sha224 as hash_class

from django import forms

from amcat.forms.widgets import BootstrapMultipleSelect
from amcat.models import ArticleSet
from amcat.scripts.script import Script
from amcat.tools import amcates

log = logging.getLogger(__name__)

STATIC_FIELDS = ["text", "title", "date", "url"]

class DeduplicateSet(Script):
    """
    Deduplicate an articleset, optionally using a limited set of fields
    """

    class options_form(forms.Form):
        articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
        ignore_fields = forms.MultipleChoiceField(choices=[(f, f) for f in STATIC_FIELDS],
                                                  required=False,
                                                  widget=BootstrapMultipleSelect)
        save_duplicates_to = forms.CharField(initial="", required=False,
                                             help_text="If not empty, save duplicates to new set with this name.")

        dry_run = forms.BooleanField(initial=False, required=False,
                                     help_text="Prints all duplicates but doesn't remove them")

        def __init__(self, *args, articleset=None, **kwargs):
            super().__init__(*args, **kwargs)
            articleset = articleset or kwargs.get('data', {}).get('articleset')
            if isinstance(articleset, int):
                articleset = ArticleSet.objects.get(pk=articleset)
            properties = articleset.get_used_properties()
            self.fields['ignore_fields'].choices = [(f, f) for f in chain(STATIC_FIELDS, properties)]

    def _run(self, articleset, save_duplicates_to, dry_run, ignore_fields, **_):
        hashes = collections.defaultdict(set)
        for i, (id, h) in enumerate(self.hash_articles(articleset, set(ignore_fields))):
            if not i % 100000:
                logging.info("Collecting hashes, n={i}, |hashes|={n}".format(n=len(hashes), **locals()))
            hashes[h].add(id)

        hashes = {hash: ids for (hash, ids) in hashes.items() if len(ids) > 1}
        logging.info("Duplicates founds for {} articles".format(len(hashes)))

        to_remove = set()
        logging.info("Iterating over hashes")
        for i, (hash, ids) in enumerate(hashes.items()):
            if dry_run:
                logging.info("Duplicates: {ids}".format(**locals()))
            to_remove |= set(sorted(ids)[1:])
            if not i % 100000:
                logging.info("Iterating over hashes {i}/{n}, |to_remove|={m}".format(n=len(hashes), m=len(to_remove),
                                                                                     **locals()))

        n = len(to_remove)
        if not to_remove:
            logging.info("No duplicates found!")
        else:
            if dry_run:
                logging.info("{n} duplicate articles found, run without dry_run to remove".format(**locals()))
            else:
                logging.info("Removing {n} articles from set".format(**locals()))
                articleset.remove_articles(to_remove)
            if save_duplicates_to:
                dupes_article_set = ArticleSet.create_set(articleset.project, save_duplicates_to, to_remove)
        return n, dry_run

    @classmethod
    def hash_articles(cls, articleset: ArticleSet, ignore_fields: set) -> Iterable[Tuple[int, str]]:
        """
        Finds all articles in an articleset, and hashes articles as a tuple of field values, ordered alphabetically
        by field name. Fields in ignore_fields will not affect the hash.
        Hashes for two articles are equal, if and only if for each field that is not in ignore_fields, the
        values of thoses fields are equal in both articles.

        @param articleset       The articleset that is to be searched
        @param ignore_fields    A set of fields that should not be included in the calculated hashes

        @return                 An iterable of (<article_id>, <hash>) tuples.
        """
        all_fields = STATIC_FIELDS + list(articleset.get_used_properties())

        if not ignore_fields:
            fields = ["hash"]
        else:
            fields = sorted(f for f in all_fields if not f in ignore_fields)

        x = amcates.ES().scan(query={"query": {"constant_score": {"filter": {"term": {"sets": articleset.id}}}}},
                              fields=fields)
        for x in amcates.ES().scan(query={"query": {"constant_score": {"filter": {"term": {"sets": articleset.id}}}}},
                                   fields=fields):
            if not ignore_fields:
                yield int(x['_id']), x['fields']['hash'][0]
                continue
            art_tuple = tuple(str(x['fields'].get(k, [None])[0]) for k in fields)
            hash = hash_class(repr(art_tuple).encode()).hexdigest()
            yield int(x['_id']), hash


if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli
    run_cli()
