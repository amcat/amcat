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

from django.conf.urls import patterns, url
from django.contrib.auth.views import password_change, password_change_done

from navigator.views.preprocessing_views import ProcessParsingView
from navigator.views import rule_views

from navigator.views.articleset_views import *
from navigator.views.article_views import *
from navigator.views.query import *
from navigator.views.project_views import *
from navigator.views.codebook_views import *
from navigator.views.user_views import *
from navigator.views.codingjob_views import *
from navigator.views.codingschema_views import *

urlpatterns = patterns(
    '',
     url(r'^$', 'navigator.views.report.index', name="index"),

    # User report
    url(r'^users$', 'navigator.views.user.my_affiliated_active', name='users'),
    url(r'^users/my_all$', 'navigator.views.user.my_affiliated_all'),
    url(r'^users/all$', 'navigator.views.user.all', name='all-users'),

    url(r'^media$', 'navigator.views.report.media', name='media'),
    url(r'^nyi$', 'navigator.views.nyi.index', name='nyi'),
    
    # Articles
    url(r'^project/(?P<project_id>[0-9]+)/article/(?P<article_id>[0-9]+)$',
            'navigator.views.article.view', name="article"),
    url(r'^project/(?P<project_id>[0-9]+)/article/(?P<article_id>[0-9]+)/remove_from/(?P<remove_articleset_id>[0-9]+)$',
            'navigator.views.article.remove_from', name="remove_from_articleset"),
    #url(r'^project/(?P<project_id>[0-9]+)/article/(?P<article_id>[0-9]+)$',
    #        'navigator.views.project.article', name="article"),
    url(r'^project/(?P<projectid>[0-9]+)/processparsing$',
        ProcessParsingView.as_view(), name="processparsing"),
    # parses
    url(r'^project/(?P<projectid>[0-9]+)/analysedarticle/(?P<id>[0-9]+)$',
        'navigator.views.article.analysedarticle', name='analysedarticle'),
    url(r'^project/(?P<projectid>[0-9]+)/analysedsentence/(?P<id>[0-9]+)$',
        'navigator.views.article.analysedsentence', name='analysedsentence'),
    url(r'^project/(?P<projectid>[0-9]+)/analysedsentence/(?P<id>[0-9]+)/ruleset/(?P<rulesetid>[0-9]+)$',
        'navigator.views.article.analysedsentence', name='analysedsentence-ruleset'),

    
    url(r'^ruleset/(?P<pk>[0-9]+)$', rule_views.RuleSetView.as_view(), name='ruleset'),
    url(r'^ruleset$', rule_views.RuleSetTableView.as_view(), name='ruleset-list'),
    
    # Media
    url(r'^medium/add$', 'navigator.views.medium.add', name='medium-add'),
    url(r'^medium/add-alias$', 'navigator.views.medium.add_alias', name='medium-alias-add'),

    # Users
    url(r'^user/(?P<id>[0-9]+)?$', 'navigator.views.user.view', name='user'),
    url(r'^user/edit/(?P<id>[0-9]+)$', 'navigator.views.user.edit', name='user-edit'),
    url(r'^user/add$', 'navigator.views.user.add', name='user-add'),
    url(r'^user/add-submit$', 'navigator.views.user.add_submit', name='user-add-submit'),
    url(r'^user/change-password$', password_change, name='user-change-password',
        kwargs=dict(
            template_name="navigator/user/change_password.html",
            post_change_redirect='change-password-done'
        )),
    url(r'^user/change-password-done$', password_change_done, name='change-password-done',
        kwargs=dict(
            template_name="navigator/user/change_password_done.html"
        )),

    # Coding
    url(r'^coding/schema-editor$', 'navigator.views.schemas.index'),
    url(r'^coding/codingschema/(?P<id>[0-9]+)$', 'navigator.views.schemas.schema',
        name='codingschema'),

    url(r'^codingjobs/(?P<coder_id>\d+)?$' ,'navigator.views.codingjob.index', name='codingjobs'),
    url(r'^codingjobs/(?P<coder_id>\d+)/all$' ,'navigator.views.codingjob.all', name='codingjobs-all'),
    
    # Scrapers
    url(r'^scrapers$', 'navigator.views.scrapers.index', name='scrapers'),


    url(r'^semanticroles$', 'navigator.views.semanticroles.index', name='semanticroles'),
    url(r'^semanticroles/(?P<id>[0-9]+)$', 'navigator.views.semanticroles.sentence', name='semanticroles-sentence'),
) 


for view in [ProjectDetailsView, ArticleSetListView, ArticleSetDetailsView,
             ArticleSetArticleDetailsView, ProjectArticleDetailsView, ArticleRemoveFromSetView,
             ArticleSetUploadView,ArticleSetUploadListView,
             QueryView, ArticleSetSampleView, ArticleSetEditView,ArticleSetImportView,ArticleSetRefreshView,
             ArticleSetDeleteView,ArticleSetUnlinkView,
             ArticleSplitView,
             CodebookListView, CodebookDetailsView, CodebookImportView, CodebookLinkView, ExportCodebook,
             CodebookUnlinkView, CodebookDeleteView, CodebookAddView,
             CodebookChangeNameView, CodebookSaveChangesetsView,CodebookSaveLabelsView,
             CodingSchemaListView, CodingSchemaDetailsView, CodingSchemaDeleteView, CodingSchemaCreateView,
             CodingSchemaEditView,CodingSchemaEditFieldsView,CodingSchemaEditRulesView, CodingSchemaNameView,
             CodingSchemaCopyView,CodingSchemaLinkView,CodingSchemaUnlinkView,
             CodingJobListView, CodingJobAddView, CodingJobDetailsView,CodingJobDeleteView,CodingJobEditView,
             CodingJobExportSelectView, CodingJobExportView,
             ProjectUserListView, ProjectUserAddView]:
    for pattern in view.get_url_patterns():
        urlpatterns += patterns('',
                                url(pattern, view.as_view(), name=view.get_view_name())
                            )

urlpatterns += patterns('',
                        url("^projects/(?P<project_id>[0-9]+)/$", ArticleSetListView.as_view(), name="project"),
                        url("^projects/$", ProjectListView.as_view(), name="projects"),
                        url("^projects/add/$$", ProjectAddView.as_view(), name="projects-add"),
                        url("^projects/(?P<what>[a-z]+)/$", ProjectListView.as_view(), name="projects"),
                        )
#    url(r'^projects(?P<what>/\w+)?$', 'navigator.views.project.projectlist', name='projects'),
