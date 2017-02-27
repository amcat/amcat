import base64
import functools
import json
import logging
import os
import shutil
from tempfile import mkdtemp
from typing import List
from uuid import UUID, uuid4

from django import forms
from django.core.urlresolvers import reverse
from django.http import QueryDict
from django.shortcuts import redirect
from django.utils.datastructures import MultiValueDict
from django.views.generic import FormView

import amcat.scripts.article_upload.upload_plugin
from amcat.scripts.article_upload import upload
from amcat.scripts.article_upload.upload import ArticleField, REQUIRED
from amcat.tools.amcates import ARTICLE_FIELDS, is_valid_property_name
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import BaseMixin
from navigator.views.scriptview import ScriptHandler, get_temporary_file_dict
from settings import ES_MAPPING_TYPES

log = logging.getLogger(__name__)

STORAGE_DIR = mkdtemp(prefix="amcat_upload")
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


class ArticleSetUploadScriptHandler(ScriptHandler):
    def get_redirect(self):
        aset_id = self.task._get_raw_result()
        return reverse("navigator:articleset-details", args=[self.task.project.id, aset_id]), "View set"

    def get_script(self):
        script_cls = self.task.get_class()
        kwargs = self.get_form_kwargs()
        form = script_cls.form_class(**kwargs)
        return script_cls(form)


class ArticleSetUploadForm(upload.UploadForm):
    script = forms.ChoiceField(choices=[(k, k) for k, _ in amcat.scripts.article_upload.upload_plugin.get_upload_plugins().items()])
    file = forms.FileField(help_text='Uploading very large files can take a long time. '
                                     'If you encounter timeout problems, consider uploading smaller files')

    def __init__(self, *args, project = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['script'].choices = self.get_script_choices(project)
        for field in list(self.fields):
            if field not in ("file", "articleset", "articleset_name", "encoding", "script"):
                self.fields.pop(field)

    def get_script_choices(self, project):
        return [(k, k) for k, _ in amcat.scripts.article_upload.upload_plugin.get_project_plugins(project).items()]


# Place 'file' field back on top, makes it a bit more intuitive.
ArticleSetUploadForm.base_fields.move_to_end('file', last=False)

class ArticleSetUploadView(BaseMixin, FormView):
    form_class = ArticleSetUploadForm
    parent = ProjectDetailsView
    view_name = "articleset-upload"
    url_fragment = "upload"

    def store_upload(self, upload_id, file, encoding, script, articleset, articleset_name):
        upload_dir = get_or_create_upload_dir(str(self.request.user.id), upload_id)
        file_path = os.path.join(upload_dir, file.name)

        with open(file_path, "wb") as dst:
            shutil.copyfileobj(file, dst)

        session_key = "upload__{upload_id}".format(**locals())
        self.request.session[session_key] = {"project": self.project.id,
                                             "upload_id": upload_id,
                                             "encoding": encoding,
                                             "script": script,
                                             "filename": file_path,
                                             "articleset": articleset and articleset.id,
                                             "articleset_name": articleset_name,
                                             "size": file.size}

    def form_valid(self, form):
        upload_id = uuid4()
        upload_id_urlsafe = base64.urlsafe_b64encode(upload_id.bytes).decode()
        self.store_upload(str(upload_id), **form.cleaned_data)
        redirect_url = reverse("navigator:articleset-upload-options", args=(self.project.id,))
        return redirect("{}?upload_id={}".format(redirect_url, upload_id_urlsafe))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project'] = self.project
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
        if (cleaned_data['destination'] == NEW_FIELD) and not cleaned_data['new_name']:
            raise forms.ValidationError("Fieldname required for new field")

        if cleaned_data['new_name']:
            validate_property_name(cleaned_data['new_name'], cleaned_data['type'])
        return cleaned_data


class ArticleUploadFormSet(forms.BaseFormSet):
    management_initial = ()
    project = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.management_initial = dict(self.management_initial)
        self.form_kwargs['project'] = self.project

    @property
    def management_form(self):
        mf = super().management_form
        mf.fields["upload_id"] = forms.UUIDField(initial=self.management_initial.get("upload_id"),
                                                 widget=forms.HiddenInput)
        return mf

    def clean(self):
        required = set(REQUIRED)
        for form in self.forms:
            required.discard(form.cleaned_data.get('destination'))
        if required:
            raise forms.ValidationError("Missing required article field(s): {}".format(", ".join(required)))


class ArticlesetUploadOptionsView(BaseMixin, FormView):
    parent = ProjectDetailsView
    view_name = "articleset-upload-options"
    url_fragment = "upload-options"

    @property
    @functools.lru_cache()
    def script_fields(self) -> List[ArticleField]:
        return list(self.script_class.get_fields(self.upload['filename'], self.upload['encoding']))

    @property
    def upload_id(self):
        return UUID(bytes=base64.urlsafe_b64decode(self.request.GET["upload_id"]))

    def get_context_data(self, **kwargs):
        kwargs['script_name'] = self.script_class.__name__
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
        formset.management_initial = {"upload_id": self.upload_id}
        return formset

    @property
    def upload(self):
        key = "upload__{self.upload_id}".format(**locals())
        return self.request.session[key]

    @property
    def script_class(self):
        plugin = amcat.scripts.article_upload.upload_plugin.get_upload_plugin(self.upload['script'])
        cls = plugin.script_cls
        return cls


    def get_script_form_kwargs(self, upload, fieldmap):
        data = {k: upload[k] for k in ("project", "articleset", "articleset_name", "encoding")}
        data['field_map'] = json.dumps(fieldmap)
        data['filename'] = self.upload['filename']
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


def get_or_create_upload_dir(upload_id: str, user_id):
    dir = os.path.join(STORAGE_DIR, str(user_id), upload_id)
    os.makedirs(dir, exist_ok=True)
    return dir
