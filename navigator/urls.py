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

from django.conf.urls import url
from django.contrib.auth.views import password_change, password_change_done

import navigator.views.codingjob
import navigator.views.index
import navigator.views.request_token
import navigator.views.user


from navigator.views.article_views import *  # noqa
from navigator.views.articleset_upload_views import * # noqa
from navigator.views.articleset_views import *  # noqa
from navigator.views.codebook_views import *  # noqa
from navigator.views.codingjob_views import *  # noqa
from navigator.views.codingschema_views import *  # noqa
from navigator.views.project_views import *  # noqa
from navigator.views.query import *  # noqa
from navigator.views.remote_import import * # noqa
from navigator.views.task import TaskDetailsView, TaskListView, clean_ready, clean_stuck, uuid_redirect
from navigator.views.user_views import *  # noqa

import navigator.utils.error_handlers

UUID_RE = "[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"

urlpatterns = [
    url(r'^$', navigator.views.index.index, name="index"),

     # Users
    url(r'^user/(?P<id>[0-9]+)?$', navigator.views.user.view, name='user'),
    url(r'^user/edit/(?P<id>[0-9]+)$', navigator.views.user.edit, name='user-edit'),
    url(r'^user/change-password$', password_change, name='user-change-password',
        kwargs=dict(
            template_name="change_password.html",
            post_change_redirect='navigator:change-password-done'
        )),
    url(r'^user/change-password-done$', password_change_done, name='change-password-done',
        kwargs=dict(
            template_name="change_password_done.html"
        )),


    url(r'^codingjobs/?$' ,navigator.views.codingjob.index, name='codingjobs'),

    # Task actions
    url(r'^projects/(?P<project>[0-9]+)/tasks/clean_ready', clean_ready, name='task-clean-ready'),
    url(r'^projects/(?P<project>[0-9]+)/tasks/clean_stuck', clean_stuck, name='task-clean-stuck'),
    url(r'^projects/(?P<project>[0-9]+)/tasks/(?P<uuid>%s)' % UUID_RE, uuid_redirect, name='task-uuid'),
    url(r'^to_object$', navigator.views.index.to_object, name='to_object'),
    url(r'^request_token$', navigator.views.request_token.RequestTokenView.as_view(), name='request_token'),
]

_views = [
    ProjectDetailsView, ArticleSetListView, ArticleSetDetailsView, ArticleSetCreateView,
    ArticleSetArticleDetailsView, ProjectArticleDetailsView, ArticleRemoveFromSetView,
    ArticleSetUploadView, ArticlesetUploadOptionsView,
    ClearQueryCacheView, QuerySetSelectionView, QueryView,  QueryListView, QuerySetArchivedView,
    SavedQueryRedirectView, ArticleSetSampleView,
    ArticlesSetFileUploadView, UploadListView,
    ArticleSetEditView, ArticleSetImportView, ArticleSetRefreshView,
    ArticleSetDeleteView, ArticleSetUnlinkView, ArticleSetDeduplicateView, 
    ArticleSplitView, ArticleSetFavouriteView,

    CodebookListView, CodebookDetailsView, CodebookImportView, CodebookLinkView,
    ExportCodebook, CodebookUnlinkView, CodebookDeleteView, CodebookAddView,
    CodebookChangeNameView, CodebookSaveChangesetsView,CodebookSaveLabelsView, CodebookAddCodeView,

    CodingSchemaListView, CodingSchemaDetailsView, CodingSchemaDeleteView, CodingSchemaCreateView,
    CodingSchemaEditView,CodingSchemaEditFieldsView,CodingSchemaEditRulesView, CodingSchemaNameView,
    CodingSchemaCopyView,CodingSchemaLinkView,CodingSchemaUnlinkView, CodingJobListView,
    CodingJobAddView, CodingJobDetailsView,CodingJobDeleteView, CodingJobEditView,
    CodingJobExportSelectView, CodingJobExportView, CodingJobLinkActionFormView,

    ProjectUserListView, ProjectUserAddView, ProjectUserInviteView,

    UserTokenView,

    RemoteArticleSetImportView,

    TaskDetailsView, TaskListView,
    MultipleArticleSetDestinationView,
]

for view in _views:
    for pattern in view.get_url_patterns():
        urlpatterns.append(
            url(pattern, view.as_view(), name=view.get_view_name())
        )

urlpatterns += [
    url("^projects/(?P<project>[0-9]+)/$", ArticleSetListView.as_view(), name="project"),
    url("^projects/$", ProjectListView.as_view(), name="projects"),
    url("^projects/add/$", ProjectAddView.as_view(), name="projects-add"),
    url("^projects/(?P<what>[a-z]+)/$", ProjectListView.as_view(), name="projects"),
]
#    url(r'^projects(?P<what>/\w+)?$', 'navigator.views.project.projectlist', name='projects'),
