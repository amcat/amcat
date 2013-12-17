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

from .articleset_views import ArticleSetDetailsView
from amcat.models import Article
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin
from django.views.generic.detail import DetailView

class ArticleSetArticleDetailsView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, DetailView):
    parent = ArticleSetDetailsView
    model = Article
    context_category = 'Articles'

class ProjectArticleDetailsView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DetailView):
    model = Article
    parent = None
    base_url = "projects/(?P<project_id>[0-9]+)"
    context_category = 'Articles'
    template_name = 'project/article_details.html'
    url_fragment = "articles/(?P<article_id>[0-9]+)"

    @classmethod
    def _get_breadcrumb_name(cls, kwargs, view):
        a = view.object
        return "Article {a.id} : {a}".format(**locals())
    @classmethod
    def get_view_name(cls):
        return "project-article-details"
