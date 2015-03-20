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

import sys
import datetime

from amcat.management.commands.upgrade_hashes import GROUP_SIZE
from django.core.management import BaseCommand
from amcat.models import Article
from amcat.tools import amcates
from amcat.tools.amcates import get_article_dict
from amcat.tools.toolkit import grouper


class Command(BaseCommand):
    help = 'Reindex existing articles in elasticsearch database, using postgres data. Does not' \
           'update hash or set membership.'

    def handle(self, *args, **options):
        es = amcates.ES()

        print("Counting articles..", end=" ")
        sys.stdout.flush()
        narticles = es.count(query="*", filters={})
        print(narticles)

        then, now = datetime.datetime.now(), datetime.datetime.now()
        for i, article_ids in enumerate(grouper(es.query_ids(), n=GROUP_SIZE)):
            progress = (float(i * GROUP_SIZE) / float(narticles)) * 100
            print("{} of {} ({:.2f}%)".format(i*GROUP_SIZE, narticles, progress))

            articles = Article.objects.filter(id__in=article_ids).select_related("medium")
            article_dicts = map(get_article_dict, articles)

            for article_dict in article_dicts:
                del article_dict["sets"]
                del article_dict["hash"]

            es.bulk_update_values({a["id"]: a for a in article_dicts})

            then, now = now, datetime.datetime.now()
            print("Articles per second: ", end="")
            print(int(GROUP_SIZE / (now - then).total_seconds()))

        print("Done.")
