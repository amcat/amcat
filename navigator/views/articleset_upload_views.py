import base64
import logging
import os
from tempfile import mkdtemp
from uuid import uuid4, UUID
import json

from django import forms
from django.contrib.postgres.forms import JSONField
from django.core.files.uploadedfile import UploadedFile
from django.core.urlresolvers import reverse
from django.http import QueryDict
from django.shortcuts import redirect
from django.utils.datastructures import MultiValueDict
from django.views.generic import FormView

from amcat.models import Plugin, ArticleSet

from amcat.scripts.article_upload import upload
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import BaseMixin
from navigator.views.scriptview import ScriptHandler, get_temporary_file_dict

log = logging.getLogger(__name__)
STORAGE_DIR = mkdtemp(prefix="amcat_upload")

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

        for k, v in arguments['files'].items():
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


    def get_script(self):
        script_cls = self.task.get_class()
        kwargs = self.get_form_kwargs()
        form = script_cls.form_class(**kwargs)
        return script_cls(form)


class ArticleSetUploadForm(upload.UploadForm):
    script = forms.ModelChoiceField(queryset=Plugin.objects.all())
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in list(self.fields):
            if field not in ("file", "articleset", "articleset_name", "encoding", "script"):
                self.fields.pop(field)

class ArticleSetUploadView(BaseMixin, FormView):
    form_class = ArticleSetUploadForm
    parent = ProjectDetailsView
    view_name = "articleset-upload"
    url_fragment = "upload"

    def store_upload(self, upload_id, file, encoding, script, articleset, articleset_name):
        dir = get_or_create_upload_dir(str(self.request.user.id), upload_id)
        file_path = os.path.join(dir, file.name)
        with open(file_path, "wb") as f:
            f.seek(0)
            for chunk in file.chunks():
                f.write(chunk)
            f.flush()
        ses = self.request.session
        uploads = ses.get('uploads', {})
        uploads[upload_id] = {"project": self.project.id,
                              "upload_id": upload_id,
                              "encoding": encoding,
                              "script": script.id,
                              "filename": file.name,
                              "file_path": file_path,
                              "articleset": articleset and articleset.id,
                              "articleset_name": articleset_name,
                              "size": file.size}
        ses['uploads'] = uploads

    def form_valid(self, form):
        upload_id = uuid4()
        upload_id_urlsafe = base64.urlsafe_b64encode(upload_id.bytes).decode()
        self.store_upload(str(upload_id), **form.cleaned_data)
        return redirect("{}?upload_id={}".format(reverse("navigator:articleset-upload-options", args=(self.project.id,)),
                                        upload_id_urlsafe))

class ArticleUploadFieldForm(forms.Form):
    label = forms.CharField(required=False, help_text="(Type Constant value)")
    values = forms.CharField(required=False)
    destination = forms.ChoiceField(choices=[("-", "(don't use)"),
                                             ("title", "Title"),
                                             ("date", "Date)"),
                                             ("text", "Text"),
                                             ("custom", "Custom")])

from django.forms import BaseFormSet
class ArticleUploadFormSet(BaseFormSet):
    # WvA: Dit lijkt niet te werken, we kunnen het field erin hacken, maar kan vast ook 'net'
    # (ik wil dus dit field op 'managementform' niveau, niet op form niveau)
    # overigens haalt ie de upload_id nu gewoon uit de GET params volgens mij, ook bij POST?
    upload_id = forms.UUIDField(widget=forms.HiddenInput)
    
    
class ArticlesetUploadOptionsView(BaseMixin, FormView):
    parent = ProjectDetailsView
    view_name = "articleset-upload-options"
    url_fragment = "upload-options"

    @property
    def script_fields(self):
        # We don't want to parse files multiple times, so cache value
        try: 
            return self._script_fields
        except AttributeError:
            self._script_fields = list(self.script_class.get_fields(
                self.uploaded_file, self.upload['encoding']))
            return self._script_fields
        
    @property
    def upload_id(self):
        return UUID(bytes=base64.urlsafe_b64decode(self.request.GET["upload_id"]))

    def get_context_data(self, **kwargs):
        kwargs['script_name'] = self.script_class.__name__
        return super().get_context_data(**kwargs)

    def initial_data(self):
        def abbrev(x, maxlen):
            x = str(x).strip()
            if len(x) > maxlen: x = x[:maxlen] + "..."
            return x
            
        for f in self.script_fields:
            values = ",".join(abbrev(x, 20) for x in f.values)
            yield {'label': f.label, 'values': values, 'destination': f.suggested_destination}
    def get_initial(self):
        return list(self.initial_data())
        
    def get_form_class(self):
        from django.forms import formset_factory
        return formset_factory(ArticleUploadFieldForm, formset=ArticleUploadFormSet)

    @property
    def upload(self):
        return self.request.session['uploads'][str(self.upload_id)]

    @property
    def script_class(self):
        script = Plugin.objects.get(id=self.upload['script']).get_class()
        return script

    @property
    def uploaded_file(self):
        filename = self.upload["filename"]
        return UploadedFile(
            name=filename,
            file=open(self.upload['file_path'], "rb"),
            size=self.upload["size"]
        )

    def get_script_form_kwargs(self, upload, fieldmap):
        data = {k: upload[k] for k in ("project", "articleset", "articleset_name", "encoding")}
        data['field_map'] = json.dumps(fieldmap)
        files = {"file": self.uploaded_file}

        return {"data": data, "files": files}

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

    def form_valid(self, form):
        fieldmap = {}
        for field in form:
            label = field.cleaned_data['label']
            destination = field.cleaned_data['destination']
            if label and destination and destination != "-":
                fieldmap[label] = destination
        args = self.get_script_form_kwargs(self.upload, fieldmap)
        args = self.clean_script_args(args)
        handler = ArticleSetUploadScriptHandler.call(target_class=self.script_class, arguments=args,
                            project=self.project, user=self.request.user)
        return redirect(reverse("navigator:task-details", args=(self.project.id, handler.task.id)))

def get_or_create_upload_dir(upload_id: str, user_id):
    dir = os.path.join(STORAGE_DIR, str(user_id), upload_id)
    os.makedirs(dir, exist_ok=True)
    return dir
