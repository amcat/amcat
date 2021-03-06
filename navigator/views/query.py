##########################################################################
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

import json
import logging
from uuid import uuid4

from django import conf, forms
from django.contrib.sessions.backends.base import SessionBase
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models.query_utils import Q
from django.http import HttpResponseBadRequest, HttpResponse, Http404
from django.shortcuts import redirect
from django.views.generic import ListView, FormView
from django.views.generic.base import TemplateView, RedirectView, View

import settings
from amcat.models import Query, Task, Project, CodingJob, ArticleSet
from amcat.scripts import query
from amcat.scripts.forms import SelectionForm
from amcat.scripts.query import get_r_queryactions
from amcat.scripts.query.queryaction import is_valid_cache_key, QueryAction
from amcat.tools import amcates
from amcat.tools.amcates import get_property_mapping_type
from api.rest.datatable import Datatable
from api.rest.viewsets import QueryViewSet, FavouriteArticleSetViewSet, CodingJobViewSet
from navigator.views.datatableview import DatatableMixin
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, BaseMixin, \
    ProjectActionForm, ProjectActionFormView

log = logging.getLogger(__name__)

FILTER_PROPERTIES = {"default", "tag"}

SHOW_N_RECENT_QUERIES = 5

R_PLUGIN_PLACEHOLDER = (object(), object())

CODINGJOB_AGGREGATION_ACTION = ("Graph/Table (Codings)", query.CodingAggregationAction)

QUERY_ACTIONS = (
    ("Summary", query.SummaryAction),
    ("Graph/Table (Elastic)", query.AggregationAction),
    ("Articlelist", query.ArticleListAction),
    ("Network", (
        ("Association", query.AssociationAction),
        ("Clustermap", query.ClusterMapAction)
    )),
    ("Actions", (
        ("Append to existing set", query.AppendToSetAction),
        ("Assign as codingjob", query.AssignAsCodingjobAction),
        ("Save query as codebook", query.SaveQueryToCodebookAction),
        ("Save as new set", query.SaveAsSetAction)
    )),
    R_PLUGIN_PLACEHOLDER
)

if settings.DEBUG:
    QUERY_ACTIONS += (
        ("Debug", (
            ("Statistics", query.StatisticsAction),
        ),),
    )

# get all class paths from the above QUERY_ACTIONS dict
QUERY_ACTION_CLASSES = ["{cls.__module__}.{cls.__name__}".format(cls=cls)
                        for classes in ([x] if not isinstance(x, tuple) else list(dict(x).values()) for x in
                                        dict(QUERY_ACTIONS).values())
                        for cls in classes if isinstance(cls, type) and issubclass(cls, QueryAction)]


class ClearQueryCacheView(ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, View):
    context_category = 'Query'
    parent = ProjectDetailsView
    url_fragment = 'clear-query-cache'
    view_name = 'clear-query-cache'

    http_method_names = ["post"]

    def post(self, *args, **kwargs):
        cache_key = self.request.POST.get("cache-key")

        if not is_valid_cache_key(cache_key):
            return HttpResponseBadRequest("Invalid cache key.")

        cache.set(cache_key, None)
        return HttpResponse("OK")


class SavedQueryRedirectView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, RedirectView):
    model = Query
    parent = ProjectDetailsView
    url_fragment = 'query/(?P<query>[0-9]+)'
    view_name = 'saved_query'
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        query_id = int(self.kwargs["query"])
        query = Query.objects.get(id=query_id)
        script_name = query.parameters["script"]
        sets = list(query.get_articleset_ids())
        codingjobs = list(query.get_codingjob_ids())
        url = reverse("navigator:query", args=[self.project.id])

        query_session, query_session_id = QuerySessionStore.createNew(self.request.session)

        if codingjobs:
            query_session.setJobs(codingjobs)
        else:
            query_session.setSets(sets)

        url += "?query={query_id}&query_session_id={query_session_id}#{script_name}".format(**locals())

        return url


class QuerySetSelectionForm(forms.Form):
    articlesets = forms.ModelMultipleChoiceField(queryset=ArticleSet.objects.none(), required=False)
    codingjobs = forms.ModelMultipleChoiceField(queryset=CodingJob.objects.none(), required=False)

    def clean_codingjobs(self):
        if bool(self.cleaned_data.get('articlesets')) == bool(self.cleaned_data.get('codingjobs')):
            raise ValidationError("Pick either articlesets, or codingjobs")
        return self.cleaned_data['codingjobs']


class QuerySetSelectionView(BaseMixin, FormView):
    view_name = "query_select"
    url_fragment = "queryselect"
    parent = ProjectDetailsView
    form_class = QuerySetSelectionForm

    def get_query_url(self, suffix=""):
        return reverse("navigator:query", args=[self.project.id]) + suffix

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        form.fields['articlesets'].queryset = ArticleSet.objects.filter(projectarticleset__project=self.project)
        form.fields['codingjobs'].queryset = CodingJob.objects.filter(Q(project=self.project) | Q(linked_projects=self.project))
        return form

    def form_valid(self, form):
        store, query_session_id = QuerySessionStore.createNew(self.request.session)
        if form.cleaned_data.get('articlesets'):
            store.setSets([aset.id for aset in form.cleaned_data['articlesets']])
        else:
            store.setJobs([cjob.id for cjob in form.cleaned_data['codingjobs']])

        return redirect(
            reverse('navigator:query', args=[self.project.id]) + "?query_session_id={}".format(query_session_id))

    def get_saved_queries_table(self):
        table = Datatable(
            QueryViewSet,
            url_kwargs={"project": self.project.id},
            rowlink=self.get_query_url("{id}")
        )
        table = table.filter(archived=False)
        table = table.hide("archived", "last_saved", "parameters", "project")
        return table

    def get_articlesets_table(self):
        table = Datatable(
            FavouriteArticleSetViewSet,
            url_kwargs={"project": self.project.id},
            rowlink=self.get_query_url("?sets={id}"),
            checkboxes=True
        )

        table = table.hide("favourite", "featured", "project", "provenance")
        return table

    def get_codingjobs_table(self):
        table = Datatable(
            CodingJobViewSet,
            url_kwargs={"project": self.project.id},
            rowlink=self.get_query_url("?jobs={id}"),
            checkboxes=True
        ).filter(archived=False).hide("articleset", "archived", "insertuser")
        return table

    def get_context_data(self, **kwargs):
        saved_queries_table = self.get_saved_queries_table()
        articlesets_table = self.get_articlesets_table()
        codingjobs_table = self.get_codingjobs_table()
        return dict(super().get_context_data(**kwargs), **locals())


class QueryView(ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, TemplateView):
    context_category = 'Query'
    parent = ProjectDetailsView
    url_fragment = 'query'
    view_name = 'query'

    def get_task(self, uuid):
        try:
            return Task.objects.get(uuid=uuid, class_name__in=QUERY_ACTION_CLASSES)
        except Task.DoesNotExist:
            raise Http404("Task does not exist")

    def get(self, request, *args, **kwargs):
        if "uuid" in kwargs:
            self.task = self.get_task(kwargs["uuid"])

        context = self.get_context_data(**kwargs)

        if not (context["articleset_ids"] or context["codingjob_ids"]):
            return redirect(reverse("navigator:query_select", args=[self.project.id]))
        return self.render_to_response(context)

    def _get_ids(self, key):
        if key in ("jobs", "sets") and hasattr(self, "task"):
            return self.task.arguments["codingjobs" if key == "jobs" else "articlesets"]
        else:
            return set(map(int, filter(str.isdigit, self.request.GET.get(key, "").split(","))))

    def _get_query_action(self, label, action):

        if action is query.AggregationAction and getattr(self, 'is_codingjob_query', False):
            label, action = CODINGJOB_AGGREGATION_ACTION

        if isinstance(action, type) and issubclass(action, query.QueryAction):
            return {"label": label, "name": action.get_action_name()}
        else:
            return {"label": label, "actions": [self._get_query_action(*kv) for kv in action]}

    @classmethod
    def get_url_patterns(cls):
        patterns = super().get_url_patterns()
        comps = list(super()._get_url_components())
        comps.append("(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")  # task UUID
        patterns += ["^" + "/".join(comps) + "/$"]
        return patterns

    def query_actions(self):
        query_actions = list(QUERY_ACTIONS)
        r_queryactions = sorted((q for q in get_r_queryactions()), key=lambda q: q.get_action_name())
        r_queryactions = [(q.get_action_label(), q) for q in r_queryactions]
        if self.project.r_plugins_enabled:
            idx = query_actions.index(R_PLUGIN_PLACEHOLDER)
            query_actions.insert(idx, ("R plugins", r_queryactions))
        query_actions.remove(R_PLUGIN_PLACEHOLDER)

        query_actions = [self._get_query_action(*kv) for kv in query_actions]

        return query_actions

    def get_task_form_data(self):
        if not hasattr(self, "task"):
            return {}
        return self.task.arguments["data"]

    def get_filter_properties(self, articlesets):
        used_properties = set.union(set(), *(aset.get_used_properties() for aset in articlesets))
        for prop in used_properties:
            ptype = get_property_mapping_type(prop)
            if ptype in FILTER_PROPERTIES:
                yield prop

    def get_context_data(self, **kwargs):
        query_session_id = self.request.GET.get("query_session_id", None)

        query_id = self.request.GET.get("query", "null")
        user_id = self.request.user.id

        article_ids = self._get_ids("articles")
        article_ids_lines = "\n".join(str(id) for id in article_ids)

        if query_session_id:
            session_store = QuerySessionStore.getStore(self.request.session, query_session_id)
            articleset_ids = session_store.getSets()
            codingjob_ids = session_store.getJobs()
        else:
            articleset_ids = self._get_ids("sets")
            codingjob_ids = self._get_ids("jobs")

        codingjob_ids_json = json.dumps(list(codingjob_ids))

        if codingjob_ids:
            self.is_codingjob_query = True
            all_articlesets = self.project.all_articlesets_and_coding_sets().all().only("id", "name")
            all_articlesets = all_articlesets.filter(codingjob_set__id__in=codingjob_ids)
            articleset_ids = all_articlesets.values_list("id", flat=True)
            all_codingjobs = CodingJob.objects.all_in_project(self.project)
            codingjobs = all_codingjobs.filter(id__in=codingjob_ids)
        else:
            all_codingjobs = None
            codingjobs = None
            all_articlesets = self.project.favourite_articlesets.all().only("id", "name")
            all_articlesets = all_articlesets.filter(codingjob_set__id__isnull=True)

        articlesets = self.project.all_articlesets().filter(id__in=articleset_ids).only("id", "name")
        if codingjobs is not None:
            articlesets = self.project.all_articlesets_and_coding_sets().filter(Q(pk__in=articlesets) | Q(codingjob_set__in=codingjobs))

        articlesets_names = (aset.name for aset in articlesets)
        articleset_ids_json = json.dumps(list(articleset_ids))
        codebooks = self.project.get_codebooks().order_by("name").only("id", "name")

        form = SelectionForm(
            project=self.project,
            articlesets=articlesets,
            codingjobs=codingjobs,
            data=dict(self.request.GET, **self.get_task_form_data()),
            initial={
                "datetype": "all",
                "articlesets": articlesets
            }
        )

        filter_properties = list(self.get_filter_properties(articlesets))

        statistics = amcates.ES().statistics(filters={"sets": list(articleset_ids)})
        settings = conf.settings

        saved_queries = Query.objects.filter(project=self.project)

        if self.request.user.is_anonymous():
            saved_user_queries, saved_project_queries = [], saved_queries
        else:
            saved_user_queries = saved_queries.filter(user=self.request.user)[:SHOW_N_RECENT_QUERIES]
            saved_project_queries = saved_queries.filter(~Q(user=self.request.user))[:SHOW_N_RECENT_QUERIES]

        form.fields["articlesets"].widget.attrs['disabled'] = 'disabled'
        return dict(super(QueryView, self).get_context_data(), **locals())


class QuerySessionStore:
    query_sessions_key = 'querysessions'

    def __init__(self, session: SessionBase, query_session_id):
        self.session = session
        self.query_session_id = str(query_session_id)

        self.session.setdefault(self.query_sessions_key, {})

        self.session[self.query_sessions_key].setdefault(self.query_session_id, {})
        self.query_session = self.session[self.query_sessions_key][self.query_session_id]

    def save(self):
        self.session.save()

    def setSets(self, articlesets, commit=True):
        self.query_session['codingjobs'] = []
        self.query_session['articlesets'] = list(articlesets)
        if commit:
            self.save()

    def setJobs(self, codingjobs, commit=True):
        self.query_session['articlesets'] = []
        self.query_session['codingjobs'] = list(codingjobs)
        if commit:
            self.save()

    def getSets(self):
        return self.query_session['articlesets']

    def getJobs(self):
        return self.query_session['codingjobs']

    @classmethod
    def createNew(cls, session):
        query_session_id = uuid4()
        return QuerySessionStore(session, query_session_id), query_session_id

    @classmethod
    def getStore(cls, session, query_session_id):
        return QuerySessionStore(session, query_session_id)


class QueryListView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = Query
    parent = QueryView
    context_category = 'Query'
    rowlink = './{id}'
    url_fragment = "archive"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(locals())
        return context

    def get_resource(self):
        return QueryViewSet

    def filter_table(self, table):
        table = table.rowlink_reverse('navigator:saved_query', args=[self.project.id, '{id}'])
        table = table.hide("project")
        table = table.hide("parameters")
        return table

    def get_datatable_kwargs(self):
        return {
            "url_kwargs": {
                "project": self.project.id
            },
            "checkboxes": True
        }


class QueryArchiveActionForm(ProjectActionForm):

    def run(self):
        project = self.form.cleaned_data['project']
        queries = self.form.cleaned_data['queries']
        archived = self.form.cleaned_data.get('archived', False)
        Query.objects.filter(project=project, id__in=queries).update(archived=archived)

    class form_class(forms.Form):
        archived = forms.BooleanField(required=False, initial=False)
        queries = forms.ModelMultipleChoiceField(queryset=Query.objects.all())
        project = forms.ModelChoiceField(queryset=Project.objects.all())


class QuerySetArchivedView(ProjectActionFormView):
    action_form_class = QueryArchiveActionForm
    parent = QueryListView
    url_fragment = "setarchived"
