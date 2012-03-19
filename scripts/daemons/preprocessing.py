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

"""
Daemon that checks if there are any Articles on the articles_preprocessing_queue
and adjusts the articles_analysis table as necessary
"""

from amcat.scripts.daemons.daemonscript import DaemonScript

from amcat.models.article_preprocessing import ArticlePreprocessing
from amcat.nlp.preprocessing import set_preprocessing_actions

import logging; log = logging.getLogger(__name__)

BATCH = 1000

class PreprocessingDaemon(DaemonScript):
    def run_action(self):
        aids = set()
        preprocess_ids = list()
        
        for ap in ArticlePreprocessing.objects.all()[:BATCH]:
            aids.add(ap.article_id)
            preprocess_ids.append(ap.id)

        if not aids: return False
            
        ArticlePreprocessing.objects.filter(pk__in=preprocess_ids).delete()
        log.info("Will set preprocessing on {n} articles".format(n=len(aids)))
        set_preprocessing_actions(aids)
        
        
        
        

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(PreprocessingDaemon)
    
