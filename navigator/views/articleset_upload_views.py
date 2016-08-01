import logging
from tempfile import mkdtemp

import itertools
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import UploadedFile
from django.core.urlresolvers import reverse
from django.forms import forms
from django.shortcuts import redirect
from django.utils.datastructures import MultiValueDict
from django.views.generic import ListView
from formtools.wizard.views import SessionWizardView

from amcat.models import Plugin, OrderedDict
from amcat.scripts.article_upload.fileupload import FileUploadForm
from amcat.scripts.article_upload.upload import UploadForm
from amcat.scripts.article_upload.upload_formtools import BaseFieldMapFormSet
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
        arguments = cls.serialize_files(arguments)
        return arguments


class DummyOptionsForm(UploadForm):
    pass


class WizardForm:
    form_list = None
    inner_form = None

    def __repr__(self):
        return "<{}: inner_form: {}>".format(self.__class__.__name__, repr(self.inner_form))

    def get_inner_form(self, form_kwargs):
        return self.inner_form(**form_kwargs)


class UploadWizardForm(WizardForm):
    """
    Automatically generates a WizardForm for the given upload form. Splits the form into two steps: one step for the
    fields defined in UploadForm and FileUploadForm, the other step contains all other additional option fields.
    If the form does not contain any additional options this second step will be omitted.
    """
    field_blacklist = {"project"}

    def __init__(self, inner_form):
        super().__init__()

        self.inner_form = inner_form

        form_list = self.get_form_list()
        self.form_list = OrderedDict((str(k), v) for k, v in enumerate(form_list))

    def get_form_list(self):
        form_fields = self.inner_form().fields
        field_dicts = [OrderedDict()]
        upload_fields = self.get_upload_step_form().base_fields
        field_dicts[0].update((name, field) for name, field in form_fields.items()
                              if name in upload_fields and name not in self.field_blacklist)
        other_fields = OrderedDict((name, field) for name, field in form_fields.items()
                                   if name not in field_dicts[0] and name not in self.field_blacklist)
        if other_fields:
            field_dicts.append(other_fields)
        return [self.get_partial_form(self.inner_form, fs) for fs in field_dicts]

    @staticmethod
    def get_partial_form(base_form, fields):
        """
        Generates a form from the given base form and the fields to be included.
        """

        class PartialForm(forms.BaseForm):
            def __init__(self, file_info=None, *args, **kwargs):
                super().__init__(*args, **kwargs)

        PartialForm.__name__ = "Partial{}".format(base_form.__class__.__name__)
        setattr(PartialForm, "base_fields", fields.copy())
        for name in fields:
            clean_fn = "clean_{}".format(name)
            if hasattr(base_form, clean_fn):
                setattr(PartialForm, clean_fn, getattr(base_form, clean_fn))
        if hasattr(base_form, "clean"): setattr(PartialForm, "clean", base_form.clean)
        return PartialForm

    class DefaultUploadStepForm(UploadForm, FileUploadForm):
        pass

    @classmethod
    def get_upload_step_form(cls):
        """
        Returns the form that is to be used for the file upload step.
        """
        return cls.DefaultUploadStepForm


class WizardFormView(SessionWizardView):
    form_list = (
    DummyOptionsForm,)  # hack: SessionWizardView expects a non-empty form list at init for no reason whatsoever

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ArticleSetUploadView(BaseMixin, WizardFormView):
    parent = ArticleSetUploadListView
    view_name = "articleset-upload"
    template_name = "project/articleset_upload.html"
    file_storage = FileSystemStorage(location=mkdtemp(prefix="upload_wiz"))

    def dispatch(self, request, *args, **kwargs):
        self.options_step = next(k for k, v in self.form_list.items() if v is DummyOptionsForm)
        self.wizard_form = self.get_wizard_form(self.script_class)
        self.form_list = self.wizard_form.form_list
        return super(ArticleSetUploadView, self).dispatch(request, *args, **kwargs)

    @cached
    def _get_script_class(self):
        return Plugin.objects.get(pk=self.kwargs['plugin']).get_class()

    @property
    def script_class(self):
        return self._get_script_class()

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        prev_step = self.get_prev_step(step)
        if prev_step:
            prev_data = dict(self.get_cleaned_data_for_step(prev_step), project=self.project.id)
            prev_form = self.wizard_form.get_upload_step_form()(prev_data, files={'file': prev_data['file']})
            prev_form.full_clean()
            if 'file' in prev_form.cleaned_data and hasattr(self.wizard_form, 'get_file_info'):
                kwargs['file_info'] = self.wizard_form.get_file_info(prev_form)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(ArticleSetUploadView, self).get_context_data(**kwargs)
        context["script_name"] = self.script_class.__name__
        context["is_field_mapping_form"] = isinstance(context['form'], BaseFieldMapFormSet)
        return context

    def get_all_raw_data(self, form_dict):
        data = MultiValueDict()
        for step in self.form_list:
            form_fields = form_dict[step].data.lists()
            form_files = form_dict[step].files.items()
            for k, vs in form_fields:
                data.setlist(k.replace("{}-".format(self.get_form_prefix(step)), ""), vs)
            for k, f in form_files:
                data[k.replace("{}-".format(self.get_form_prefix(step)), "")] = f

        return data

    def done(self, form_list, form_dict, **kwargs):
        data = {}
        form_fields = self.script_class.options_form().fields
        for k, v in self.get_all_cleaned_data().items():
            data[k] = form_fields[k].prepare_value(v)


        data["project"] = self.project.id

        arguments = {
            "data": data,
            "files": {}
        }

        task = ArticleSetUploadScriptHandler.call(self.script_class,
                                                  user=self.request.user,
                                                  project=self.project,
                                                  arguments=arguments)

        return redirect(reverse("navigator:task-details", args=[self.project.id, task.task.id]))

    def get_wizard_form(self, script_class):
        if hasattr(script_class.options_form, 'as_wizard_form'):
            return script_class.options_form.as_wizard_form()(script_class.options_form)
        return UploadWizardForm(script_class.options_form)
