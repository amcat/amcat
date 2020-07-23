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

from django.core.management import BaseCommand
from amcat.models import ArticleSet, ProjectArticleSet
import logging

def reindex_sets(sets, full_refresh=True):
    logging.info(f"Reindexing {len(sets)} articlesets: {sets}")
    for i, setid in enumerate(sets):
        logging.info(f"[{i:4}/{len(sets):4}] Reindexing set {setid}")
        ArticleSet.objects.get(pk=setid).refresh_index(full_refresh=full_refresh)

    
class Command(BaseCommand):
    help = 'Reindex one or more projects or sets'
    
    def add_arguments(self, parser):
        parser.add_argument("projectid", nargs="+", help="Project ID(s) or 'all'")
        parser.add_argument("--full", action='store_true', help="Full refresh (article content as well as set membership)")
        
    def handle(self, *args, **options):
        p = options['projectid']
        if p == ['all']:
            logging.info(f"Reindexing all projects (full_refresh={options['full']}), retrieving set list")
            sets = sorted(ArticleSet.objects.all().values_list('pk', flat=True))
        else:
            projectids = [int(x) for x in p]
            logging.info("Reindexing projects {projectids} (full_refresh={options['full']}), retrieving set list")
            sets = sorted(ProjectArticleSet.objects.filter(project_id__in=projectids).values_list('articleset_id', flat=True))
        reindex_sets(sets, full_refresh=options['full'])
    
        
