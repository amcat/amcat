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
from __future__ import print_function
import datetime
from itertools import izip_longest
from django.core.management import BaseCommand
import sys
from amcat.models import Article
from amcat.tools import amcates
from amcat.tools.amcates import _get_hash

GROUP_SIZE = 10000


def grouper(iterable, n=GROUP_SIZE):
    """Collect data into fixed-length chunks or blocks"""
    return izip_longest(*[iterable] * n)


class Command(BaseCommand):
    help = 'Recalculate and update hashes in elasticsearch database.'

    def handle(self, *args, **options):
        es = amcates.ES()

        print("Counting articles..", end=" ")
        sys.stdout.flush()
        narticles = es.count(query="*", filters={})
        print(narticles)

        then, now = datetime.datetime.now(), datetime.datetime.now()
        for i, article_ids in enumerate(grouper(es.query_ids())):
            progress = (float(i * GROUP_SIZE) / float(narticles)) * 100
            print("{} of {} ({:.2f}%)".format(i*GROUP_SIZE, narticles, progress))
            articles = Article.objects.in_bulk(article_ids).values()
            es.bulk_update_values({a.id: {"hash": _get_hash(a)} for a in articles})

            then, now = now, datetime.datetime.now()
            print("Articles per second: ", end="")
            print(int(GROUP_SIZE / (now - then).total_seconds()))

        print("Done.")
