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
import tqdm
import multiprocessing

from multiprocessing.pool import Pool
from django.core.management import BaseCommand

from amcat.models import ArticleSet


def refresh(aset_id):
    ArticleSet.objects.get(aset_id)._refresh_property_cache()


class Command(BaseCommand):
    help = 'Recalculate all flexible properties caches.'

    def add_arguments(self, parser):
        parser.add_argument('--parallel', type=int, default=multiprocessing.cpu_count())

    def handle(self, *args, **options):
        threads = options["parallel"]
        articleset_ids = ArticleSet.objects.values_list("id", flat=True)
        results = Pool(threads).imap_unordered(refresh, articleset_ids)
        list(tqdm.tqdm(results, total=len(articleset_ids)))
