
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

from amcat.scripts.script import Script
from amcat.models import ArticleSet
from hashlib import sha224 as hash_class
from django import forms
from amcat.tools import amcates
import json
import collections

FIELDS = ["text", "title", "date", "creator", "medium", "byline", "section", "page", "addressee", "length"]

class DeduplicateSet(Script):
    """
    Deduplicate an articleset, optionally using a limited set of fields
    """

    class options_form(forms.Form):
        articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
        skip_text = forms.BooleanField(initial=False, required=False,
                                       help_text="Ignore full text when finding duplicates")
        skip_title = forms.BooleanField(initial=False, required=False,
                                           help_text="Ignore title when finding duplicates")
        skip_date = forms.BooleanField(initial=False, required=False,
                                       help_text="Ignore date when finding duplicates")
        skip_creator = forms.BooleanField(initial=False, required=False,
                                          help_text="Ignore creator when finding duplicates")
        skip_medium = forms.BooleanField(initial=False, required=False,
                                         help_text="Ignore medium when finding duplicates")
        skip_byline = forms.BooleanField(initial=False, required=False,
                                         help_text="Ignore byline when finding duplicates")
        skip_section = forms.BooleanField(initial=False, required=False,
                                         help_text="Ignore section when finding duplicates")
        skip_page = forms.BooleanField(initial=False, required=False,
                                         help_text="Ignore page when finding duplicates")
        skip_addressee = forms.BooleanField(initial=False, required=False,
                                            help_text="Ignore addressee when finding duplicates")
        skip_length = forms.BooleanField(initial=False, required=False,
                                         help_text="Ignore length when finding duplicates")
        save_duplicates_to = forms.CharField(initial="", required=False, 
                                             help_text="If not empty, save duplicates to new set with this name.")

        dry_run = forms.BooleanField(initial=False, required=False,
                                     help_text="Prints all duplicates but doesn't remove them")

    def _run(self, articleset, save_duplicates_to, dry_run, **_):
        hashes = collections.defaultdict(set)
        for i, (id, h) in enumerate(self.get_hashes()):
            if not i%100000:
                logging.info("Collecting hashes, n={i}, |hashes|={n}".format(n=len(hashes), **locals()))
            hashes[h].add(id)

        hashes = {hash: ids for (hash, ids) in hashes.items() if len(ids)>1}
        logging.info("Duplicates founds for {} articles".format(len(hashes)))

        to_remove = set()
        logging.info("Iterating over hashes")
        for i, (hash, ids) in enumerate(hashes.items()):
            if dry_run:
                logging.info("Duplicates: {ids}".format(**locals()))
            to_remove |= set(sorted(ids)[1:])
            if not i % 100000:
                logging.info("Iterating over hashes {i}/{n}, |to_remove|={m}".format(n=len(hashes), m=len(to_remove), **locals()))

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

    def get_hashes(self):
        fields =  [f for f in FIELDS if not self.options.get("skip_{}".format(f))]
        if fields == FIELDS:
            fields = ["hash"]
        setid = self.options['articleset'].id
        for x in amcates.ES().scan(query={"query" : {"constant_score" : {"filter": {"term": {"sets": setid}}}}},
                                   fields=fields):
            if fields == ["hash"]:
                hash = x['fields']['hash'][0]
            else:
                def get(flds, f):
                    val = flds.get(f)
                    return val[0] if val is not None else val
                    
                d = {f: get(x['fields'], f) for f in fields}
                hash = hash_class(json.dumps(d)).hexdigest()
            yield int(x['_id']), hash


if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli
    run_cli()
