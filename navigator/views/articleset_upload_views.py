import logging
from tempfile import mkdtemp

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import UploadedFile
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.views.generic import ListView
from formtools.wizard.views import SessionWizardView

from amcat.models import Plugin, OrderedDict, AmcatModel
from amcat.scripts.article_upload.upload import UploadForm
from amcat.tools.caching import cached
from api.rest.resources import PluginResource
from navigator.views.articleset_views import ArticleSetListView, UPLOAD_PLUGIN_TYPE
from navigator.views.datatableview import DatatableMixin
from navigator.views.projectview import HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, BaseMixin
from navigator.views.scriptview import ScriptHandler, get_temporary_file_dict

log = logging.getLogger(__name__)


class ArticleSetUploadListView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    parent = ArticleSetListView
    model = Plugin
    resource = PluginResource
    view_name = "articleset-upload-list"
    url_fragment = "upload"

    def filter_table(self, table):
        table = table.rowlink_reverse('navigator:articleset-upload', args=[self.project.id, '{id}'])
        return table.filter(plugin_type=UPLOAD_PLUGIN_TYPE).hide('id', 'class_name')  # , 'plugin_type')


class ArticleSetUploadScriptHandler(ScriptHandler):
    def get_redirect(self):
        aset_ids = self.task._get_raw_result()

        if len(aset_ids) == 1:
            return reverse("navigator:articleset-details", args=[self.task.project.id, aset_ids[0]]), "View set"

        # Multiple articlesets
        url = reverse("navigator:articleset-multiple", args=[self.task.project.id])
        return url + "?set=" + "&set=".join(map(str, aset_ids)), "View sets"

    @classmethod
    def serialize_models(cls, arguments):
        data = {}
        for k, v in arguments['data'].items():
            if isinstance(v, AmcatModel):
                data[k] = v.pk
            try:
                data[k] = [item.pk for item in v]
            except (TypeError, AttributeError):
                pass

        arguments['data'].update(data)
        return arguments

    @classmethod
    def serialize_files(cls, arguments):
        data = {}
        for k, v in arguments['data'].items():
            if isinstance(v, UploadedFile):
                data[k] = get_temporary_file_dict(v)
        arguments['data'].update(data)
        arguments['files'].update(data)
        return arguments

    @classmethod
    def serialise_arguments(cls, arguments):
        arguments = super().serialise_arguments(arguments)
        arguments = cls.serialize_models(arguments)
        arguments = cls.serialize_files(arguments)
        print(arguments)
        return arguments


class ArticleSetUploadFileForm(UploadForm):
    project = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DummyOptionsForm(UploadForm):
    pass


class ArticleSetUploadView(BaseMixin, SessionWizardView):
    parent = ArticleSetUploadListView
    view_name = "articleset-upload"
    template_name = "project/articleset_upload.html"
    form_list = (ArticleSetUploadFileForm, DummyOptionsForm)
    file_storage = FileSystemStorage(location=mkdtemp(prefix="upload_wiz"))

    def dispatch(self, request, *args, **kwargs):
        self.options_step = next(k for k, v in self.form_list.items() if v is DummyOptionsForm)
        self.form_list = OrderedDict(self.form_list)
        self.form_list[self.options_step] = self.script_class.options_form
        return super(ArticleSetUploadView, self).dispatch(request, *args, **kwargs)

    @cached
    def _get_script_class(self):
        return Plugin.objects.get(pk=self.kwargs['plugin']).get_class()

    @property
    def script_class(self):
        return self._get_script_class()

    def get_form_kwargs(self, step):
        kwargs = super().get_form_kwargs(step)
        return kwargs

    def get_form(self, step=None, data=None, files=None):
        if step is None:
            step = self.storage.current_step
        f = super(ArticleSetUploadView, self).get_form(step, data, files)
        if step == self.options_step:
            f.fields = OrderedDict((k, v) for k, v in f.fields.items() if k not in UploadForm.declared_fields)
            setattr(f, 'clean_articleset_name', lambda x: None)
        return f

    def get_prev_steps(self, step):
        while step is not None:
            step = self.get_prev_step(step)
            yield step

    def get_context_data(self, **kwargs):
        context = super(ArticleSetUploadView, self).get_context_data(**kwargs)
        context["script_name"] = self.script_class.__name__
        return context

    def done(self, form_list, **kwargs):
        data = self.get_all_cleaned_data()
        data["project"] = self.project.id
        arguments = {
            "data": data,
            "files": {}
        }
        print(arguments)
        task = ArticleSetUploadScriptHandler.call(self.script_class,
                                                  user=self.request.user,
                                                  project=self.project,
                                                  arguments=arguments)


        return redirect(reverse("navigator:task-details", args=[self.project.id, task.task.id]))
