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
Function for adding/removing Amcat articles to Solr from the model
"""
from __future__ import unicode_literals, print_function, absolute_import

import solr
import datetime, time
from amcat.models.article import Article
from django.db import connection
import re

import logging
log = logging.getLogger(__name__)

class GMT1(datetime.tzinfo):
    """very basic timezone object, needed for solrpy library.."""
    def utcoffset(self,dt):
        return datetime.timedelta(hours=1)
    def tzname(self,dt):
        return "GMT +1"
    def dst(self,dt):
        return datetime.timedelta(0) 
      
def _stripChars(text):
    """required to avoid:
    SolrException: HTTP code=400, reason=Illegal character ((CTRL-CHAR, code 20))  at [row,col {unknown-source}]: [3519,150]
    regexp copied from: http://mail-archives.apache.org/mod_mbox/lucene-solr-user/200901.mbox/%3C2c138bed0901040803x4cc07a29i3e022e7f375fc5f@mail.gmail.com%3E
    """
    if not text: return None
    return  re.sub('[\x00-\x08\x0B\x0C\x0E-\x1F]', ' ', text);
      
def index_articles(article_ids):
    article_ids = set(article_ids)
    to_add = set(a.id for a in Article.objects.filter(
            pk__in=article_ids, project__indexed=True, project__active=True))
    ids_to_add = set(a.id for a in to_add)
    ids_to_remove = articleids - articleidsToAdd
    
    log.debug("adding/updating %s articles, removing %s" % (len(articleidsToAdd), len(articleidsToRemove)))

    s = solr.SolrConnection('http://localhost:8983/solr')
    if to_add:
        log.debug("finding sets") # TODO: make the code below nicer
        cursor = connection.cursor()
        cursor.execute("SELECT articleset_id, article_id FROM articlesets_articles WHERE article_id in (%s)" % ','.join(map(str, ids_to_add)))
        rows = cursor.fetchall()
        log.debug("%s sets found" % len(rows))
        setsDict = collections.defaultdict(list)
        for setid, articleid in rows:
            setsDict[articleid].append(setid)

        log.debug("creating article dicts")
            
        articles = [dict(id=a.id,
                         headline=_stripChars(a.headline), 
                         body=_stripChars(a.text),
                         byline=_stripChars(a.byline), 
                         section=_stripChars(a.section),
                         projectid=a.project_id,
                         mediumid=a.medium_id,
                         date=a.date.replace(tzinfo=GMT1()),
                         sets=setsDict.get(a.id))
                    for a in to_add]
             
        log.debug("adding %s articles" % len(articlesDicts))
        s.add_many(articlesDicts)
    
    if to_remove:
        log.debug("deleting")
        s.delete_many(to_remove)
    solr.commit()

                 
if __name__ == '__main__':
    index_articles([1,2])
