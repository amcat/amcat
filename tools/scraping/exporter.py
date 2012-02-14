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

from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.models.project import Project
from amcat.models.articleset import ArticleSet

import logging
log = logging.getLogger(__name__)

ARTICLE_PROPS = [
    'date', 'section', 'pagenr', 'headline', 'byline', 'length',
    'url', 'externalid', 'text', 'parent', 'medium', 'author'
]

class Exporter(object):
    def __init__(self, set, medium=None, project=None, dummy=False):
        self.medium = medium

        if project != -1:
            self.project = Project.objects.get(id=project)
            self.set = ArticleSet(name=set, project=self.project)
            self.set.save()
        else:
            self.set = ArticleSet.objects.get(id=int(set))
            self.project = self.set.project

    def _get_medium(self, art):
        try:
            return art.medium
        except:
            return self.medium


    def commit(self, doc, return_id=True):
        if doc.id is not None:
            # Article already committed
            return doc.id if return_id else Article.objects.get(id=doc.id)

        art = Article(project=self.project)

        # All properties in ARTICLES_PROPS are set on a new Article,
        # else in Article.metastring.
        _metastring = dict()
        for prop, value in doc.getprops().items():
            if prop in ARTICLE_PROPS:
                setattr(art, prop, value)
            else:
                _metastring[prop] = value

        art.metastring = str(_metastring)
        art.medium = self._get_medium(art)

        if doc.parent:
            art.parent = self.commit(doc.parent, False)

        art.save()

        self.set.articles.add(art)
        self.set.save()

        doc.id = art.id
        return art.id if return_id else art

    def close(self):
        pass
