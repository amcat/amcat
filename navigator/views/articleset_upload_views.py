import functools
import json
import logging
import magic
import os
import urllib.parse
from typing import List

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models.fields.files import FieldFile
from django.http import QueryDict
from django.shortcuts import Http404, redirect
from django.utils.datastructures import MultiValueDict
from django.views.generic import CreateView, FormView, ListView

from amcat.models import Project, UploadedFile, User, Task
from amcat.scripts.article_upload import upload
from amcat.scripts.article_upload import magic
from amcat.scripts.article_upload.upload import ArticleField, REQUIRED, PreprocessScript
from amcat.scripts.article_upload.upload_plugins import UploadPlugin, get_project_plugins, get_upload_plugin, \
    get_upload_plugins
from amcat.tools.amcates import ARTICLE_FIELDS, is_valid_property_name
from navigator.views.datatableview import DatatableMixin
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import BaseMixin, BreadCrumbMixin, HierarchicalViewMixin, ProjectViewMixin
from navigator.views.scriptview import ScriptHandler, get_temporary_file_dict, ScriptView
from settings import ES_MAPPING_TYPES

log = logging.getLogger(__name__)

CORE_FIELDS = sorted(ARTICLE_FIELDS - {"parent_hash"})
NEW_FIELD = "new_field"


@functools.lru_cache()
def get_type_choices():
    mapping_types = set(ES_MAPPING_TYPES.keys()) - {"default"}
    return [(k, k) for k in ["default"] + sorted(mapping_types)]


def get_destination_choices(project=None):
    core_fields = [(x, x + (" *" if x in upload.REQUIRED else "")) for x in CORE_FIELDS]
    choices = [
        ("-", "(don't use)"),
        (NEW_FIELD, "New field..."),
        ("Core fields", core_fields)
    ]

    if project:
        properties = sorted(project.get_used_properties(only_favourites=True))
        if properties:
            choices.append(("Project fields", [(x, x) for x in properties]))

    return choices


class ActionFormHandler(ScriptHandler):

    def get_script(self):
        script_cls = self.task.get_class()
        kwargs = self.get_form_kwargs()
        form = script_cls.form_class(**kwargs)
        return script_cls(form)

class PreprocessScriptHandler(ActionFormHandler):
    def get_redirect(self):
        formdata = self.task.arguments['data']
        pass_data = {k: formdata[k] for k in ArticleSetUploadView.pass_fields}
        pass_data['task'] = self.task.id
        redirect_url = reverse("navigator:articleset-upload-options", args=(self.task.project.id, formdata["upload"]))
        redirect = "{}?{}".format(redirect_url, urllib.parse.urlencode(pass_data))
        return redirect, "Continue"

class ArticleSetUploadScriptHandler(ActionFormHandler):
    def get_redirect(self):
        aset_id = self.task._get_raw_result()
        return reverse("navigator:articleset-details", args=[self.task.project.id, aset_id]), "View set"

    def get_script(self):
        script_cls = self.task.get_class()
        kwargs = self.get_form_kwargs()
        form = script_cls.form_class(**kwargs)
        return script_cls(form)


class UploadListView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = UploadedFile
    parent = ProjectDetailsView
    context_category = 'Uploads'
    rowlink = './{id}'

    def filter_table(self, table):
        items = UploadedFile.get_all_active().filter(project=self.project, user=self.request.user)
        if not items:
            items = ["EMPTY"] # workaround for empty list resulting in no filter
        table = table.filter(pk__in=items)
        return table


class ArticlesetFileUploadForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"] = forms.ModelChoiceField(queryset=Project.objects.all(), widget=forms.HiddenInput)
        self.fields["user"] = forms.ModelChoiceField(queryset=User.objects.all(), widget=forms.HiddenInput)

    class Meta:
        model = UploadedFile
        fields = ["file", "project", "user"]


class ArticlesSetFileUploadView(BaseMixin, CreateView):
    parent = UploadListView
    url_fragment = 'add'
    form_class = ArticlesetFileUploadForm
    model = UploadedFile

    def get_form(self, form_class=None):
        form = super().get_form()
        form.fields['project'].initial = self.project
        form.fields['user'].initial = self.request.user
        return form

    def form_valid(self, form):
        self.instance = form.instance
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("navigator:articleset-upload", args=(self.project.id, self.instance.id))


class ArticleSetUploadForm(upload.UploadForm):
    default_choices = [(k, k) for k, _ in get_upload_plugins().items()]
    script = forms.ChoiceField(choices=default_choices, help_text='Choose the file parser script to use. More script '
                                                                  'plugins can be enabled in the project settings.')

    def __init__(self, *args, project=None, upload=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.upload = upload
        mime, enc, zip = self.get_mime(upload.file)
        if enc == "binary":
            self.fields['encoding'].choices = (("binary", "-"),)
            self.fields['encoding'].widget = forms.HiddenInput()
        self.fields['encoding'].initial = enc
        self.fields['encoding'].help_text = mime
        self.fields['script'].choices = self.get_script_choices(project, mime)
        for field in list(self.fields):
            if field not in ("articleset", "articleset_name", "encoding", "script"):
                self.fields.pop(field)

    def clean_articleset_name(self):
        if not (self.cleaned_data.get('articleset_name') or self.cleaned_data.get('articleset')):
            fn = os.path.basename(self.upload.filename)
            if fn:
                return fn
        return super().clean_articleset_name()

    def get_mime(self, file: FieldFile):
        return magic.get_mime(file.file.name)

    def get_script_choices(self, project, mime=None):
        plugins = dict(get_project_plugins(project))
        if mime is None:
            return [(k, v.label) for k, v in list(plugins.items())]

        if mime.startswith("text/x.amcat-"):
            name = mime.replace("text/x.amcat-", "")
            plugin = plugins.pop(name)
            suggested = [(name, plugin.label)]
            other = [(k, v.label) for k, v in list(plugins.items())]
            return ("Suggested", suggested), ("Other", other)

        suggested = [(k, v.label) for k, v in plugins.items() if v.supports_mime_type(mime)]
        other = [(k, v.label) for k, v in plugins.items() if not v.supports_mime_type(mime)]
        if not suggested:
            return other
        return ("Suggested", suggested), ("Other", other)

class UploadViewMixin(BaseMixin):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.upload = UploadedFile.objects.get(pk=kwargs[self.get_model_key()])
        except ObjectDoesNotExist as e:
            raise Http404(*e.args)

        return super().dispatch(request, *args, **kwargs)


class ArticleSetUploadView(UploadViewMixin, FormView):
    form_class = ArticleSetUploadForm
    parent = UploadListView
    view_name = "articleset-upload"
    pass_fields = ("encoding", "articleset_name", "articleset", "script")

    def _run_preprocess_task(self, form_data, redirect_url):
        data = dict(form_data, project=self.project.id, upload=self.upload.id)
        preprocess_task = PreprocessScriptHandler.call(
            target_class=PreprocessScript,
            arguments={"data": data},
            user=self.request.user,
            project=self.project)
        url = reverse("navigator:task-details", args=[self.project.id, preprocess_task.task.id])
        next = urllib.parse.urlencode({"next": redirect_url})
        return redirect("{url}".format(**locals()), permanent=False)


    def form_valid(self, form):
        pass_data = {k: form.data[k] for k in self.pass_fields}
        script = get_upload_plugin(form.cleaned_data['script']).script_cls
        has_preprocess = hasattr(script, "_preprocess")
        redirect_url = reverse("navigator:articleset-upload-options", args=(self.project.id, self.upload.id))
        redirect_url = "{}?{}".format(redirect_url, urllib.parse.urlencode(pass_data))
        if not has_preprocess:
            return redirect(redirect_url)
        return self._run_preprocess_task(pass_data, redirect_url)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project'] = self.project
        kwargs['upload'] = self.upload
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs['upload'] = self.upload
        return kwargs


def validate_property_name(value, type):
    if type != "default":
        value = "{}_{}".format(value, type)
    if not is_valid_property_name(value):
        raise forms.ValidationError("Invalid property name: {}".format(value))


class ArticleUploadFieldForm(forms.Form):
    label = forms.CharField(required=False, help_text="(Type Constant value)")
    destination = forms.ChoiceField(choices=get_destination_choices())

    new_name = forms.CharField(required=False)
    type = forms.ChoiceField(required=False, choices=get_type_choices())

    def __init__(self, project=None, *args, **kwargs):
        values = kwargs.get('initial', {}).pop('values', [])
        super().__init__(*args, **kwargs)
        self.values = values
        self.fields["destination"].choices = get_destination_choices(project)

    def clean(self):
        cleaned_data = super().clean()
        if self._errors:
            return cleaned_data
        if cleaned_data['destination'] == NEW_FIELD:
            if not cleaned_data['new_name']:
                raise forms.ValidationError("Fieldname required for new field")
            validate_property_name(cleaned_data['new_name'], cleaned_data['type'])

        return cleaned_data


class ArticleUploadFormSet(forms.BaseFormSet):
    management_initial = ()
    project = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_kwargs['project'] = self.project

    def clean(self):
        required = set(REQUIRED)
        for form in self.forms:
            required.discard(form.cleaned_data.get('destination'))
        if required:
            raise forms.ValidationError("Missing required article field(s): {}".format(", ".join(required)))


class ArticlesetUploadOptionsView(UploadViewMixin, FormView):
    parent = ArticleSetUploadView
    view_name = "articleset-upload-options"
    url_fragment = "upload-options"

    @property
    @functools.lru_cache()
    def script_fields(self) -> List[ArticleField]:
        if "task" in self.request.GET:
            task = Task.objects.get(id=self.request.GET["task"])
            return [ArticleField(**kwargs) for kwargs in task._get_raw_result()]
        return list(self.script_class.get_fields(self.upload.file.file.name, self.parent_form.cleaned_data['encoding']))

    @property
    @functools.lru_cache()
    def plugin(self) -> UploadPlugin:
        return get_upload_plugin(self.parent_form.cleaned_data['script'])

    @property
    def parent_form(self):
        if not hasattr(self, "_parent_form"):
            parent_form = self.parent.form_class(data=self.request.GET, project=self.get_project(), upload=self.upload)
            if parent_form.errors:
                raise Exception(self.parent_form.errors)
            self._parent_form = parent_form
        return self._parent_form

    def get_context_data(self, **kwargs):
        kwargs['plugin_name'] = self.plugin.name
        kwargs['plugin_label'] = self.plugin.label
        return super().get_context_data(**kwargs)

    def initial_data(self):
        def abbrev_and_quote(x, maxlen):
            x = str(x).strip()
            if len(x) > maxlen:
                x = x[:maxlen] + "..."
            return '{}'.format(x)

        for f in self.script_fields:
            # HACK: use initial['values'] to pass values to the respective form.__init__.
            values = [abbrev_and_quote(x, 20) for x in f.values if x] if f.values else []
            data = {'label': f.label, 'values': values}

            existing_fields = self.project.get_used_properties(only_favourites=True)
            if f.suggested_destination:
                if f.suggested_destination in CORE_FIELDS or f.suggested_destination in existing_fields:
                    data['destination'] = f.suggested_destination
                else:
                    data['destination'] = NEW_FIELD
                    data['new_name'] = f.suggested_destination.rsplit("_", 1)[0]
                    data['type'] = f.suggested_type

            yield data

    def get_initial(self):
        return list(self.initial_data())

    def get_form_class(self):
        formset = forms.formset_factory(ArticleUploadFieldForm, formset=ArticleUploadFormSet)
        formset.project = self.project
        return formset

    @property
    def script_class(self):
        cls = self.plugin.script_cls
        return cls

    def get_script_form_kwargs(self, upload, fieldmap):
        data = {
            "project": self.project.id,
            "field_map": json.dumps(fieldmap),
            "upload": self.upload.id,
            **self.parent_form.cleaned_data
        }
        return {"data": data}

    def clean_script_args(self, args):
        if isinstance(args.get('data'), QueryDict):
            args['data'] = dict(args['data'].lists())

        # Convert file objects to temporary filenames
        if isinstance(args.get('files'), MultiValueDict):
            for key in args['files'].keys():
                file_object_list = args['files'].getlist(key)
                for i, fo in enumerate(file_object_list):
                    file_object_list[i] = get_temporary_file_dict(fo)
            args['files'] = dict(args['files'])
        return args

    def format_field_name(self, name, type):
        name = "{}_{}".format(name, type) if type and type != "default" else name
        if not is_valid_property_name(name):
            raise Exception("Invalid property name: {}".format(name))
        return name

    def get_field_map(self, form):
        for i, field in enumerate(form):
            if not field.cleaned_data:
                continue
            label = field.cleaned_data['label']
            destination = field.cleaned_data['destination']
            if label and destination == "new_field":
                new_type = field.cleaned_data['type']
                new_name = field.cleaned_data['new_name']
                destination = self.format_field_name(new_name, new_type)
                yield destination, {"type": "field", "value": label}

            elif label and destination and destination != "-":
                if i < form.initial_form_count():
                    yield destination, {"type": "field", "value": label}
                else:
                    yield destination, {"type": "literal", "value": label}

    def form_valid(self, form):
        field_map = dict(self.get_field_map(form))
        args = self.get_script_form_kwargs(self.upload, field_map)
        args = self.clean_script_args(args)
        handler = ArticleSetUploadScriptHandler.call(target_class=self.script_class, arguments=args,
                                                     project=self.project, user=self.request.user)
        return redirect(reverse("navigator:task-details", args=(self.project.id, handler.task.id)))


