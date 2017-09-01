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

"""
Base module for article upload scripts
"""
import datetime
import json
import logging
import os.path
import zipfile
from typing import Any, Iterable, Sequence, Tuple, Mapping

import chardet
from actionform import ActionForm
from django import forms
from django.contrib.postgres.forms import JSONField
from django.core.files.uploadedfile import UploadedFile
from django.core.files.utils import FileProxyMixin
from django.core.serializers.json import DjangoJSONEncoder

from amcat.forms.widgets import BootstrapSelect
from amcat.models import Article, ArticleSet, Project, UploadedFile as model_UploadedFile
from amcat.models.articleset import create_new_articleset
from amcat.tools import amcates
from amcat.tools.progress import NullMonitor

log = logging.getLogger(__name__)

REQUIRED = tuple(field.name for field in Article._meta.get_fields()
                 if field.name in amcates.ARTICLE_FIELDS and not field.blank)

# HACK: Django's FileProxyMixin misses the readable and writable properties of IOBase,
# HACK: see Django ticket #26646 fixed in Django 1.11+.
if not hasattr(FileProxyMixin, 'readable'):
    setattr(FileProxyMixin, "readable", property(lambda self: getattr(self.file, 'readable', False)))
    setattr(FileProxyMixin, "writable", property(lambda self: getattr(self.file, 'writable', False)))


def validate_field_map(value):
    required = set(REQUIRED)
    name_errors = []
    for k in value.keys():
        required.discard(k)
        if not amcates.is_valid_property_name(k):
            name_errors.append(k)
    if name_errors:
        raise forms.ValidationError("Invalid property name(s): {}".format(", ".join(name_errors)))
    if required:
        raise forms.ValidationError("Missing required article field(s): {}".format(", ".join(required)))


class ArticleField(object):
    """
    Simple 'struct' to hold information about fields in uploaded files
    in order to build the 'upload options' page
    """

    def __init__(self, label, suggested_destination=None, values=None, possible_types=None, suggested_type=None):
        self.label = label  # name in uploaded file
        self.suggested_destination = suggested_destination  # suggested destination model field
        self.values = values  # top X values  
        self.possible_types = possible_types  # allowed article property types (text, date, number, integer)
        self.suggested_type = suggested_type  # suggested article property type

    def __repr__(self):
        return "<ArticleField(label={self.label}, suggested_destination={self.suggested_destination}, " \
               "suggested_type={self.suggested_type})> ".format(self=self)

    def as_fieldname(self):
        if self.suggested_type:
            return "{self.suggested_destination}_{self.suggested_type}".format(self=self)
        return self.suggested_destination


class ParseError(Exception):
    pass


class UploadForm(forms.Form):
    upload = forms.ModelChoiceField(queryset=model_UploadedFile.objects.all())
    project = forms.ModelChoiceField(queryset=Project.objects.all())

    articleset = forms.ModelChoiceField(
        queryset=ArticleSet.objects.all(), required=False,
        help_text="If you choose an existing articleset, the articles will be "
                  "appended to that set. If you leave this empty, a new articleset will be "
                  "created using either the name given below, or using the file name",
        widget=BootstrapSelect)

    articleset_name = forms.CharField(
        max_length=ArticleSet._meta.get_field('name').max_length,
        required=False)

    encoding = forms.ChoiceField(choices=[(x.lower(), x) for x in ["Autodetect", "ISO-8859-15", "UTF-8", "Latin-1"]])
    field_map = JSONField(validators=[validate_field_map],
                          help_text='json dict with property names (title, date, etc.) as keys, and field settings as values. '
                                    'Field settings should have the form {"type": "field"/"literal", "value": "field_name_or_literal"}')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'encoding' in kwargs.get('data', {}) and kwargs['data']['encoding'] == "binary":
            self.fields['encoding'].choices.append(("binary", "-"))

    def clean_articleset_name(self):
        """If articleset name not specified, use file base name instead"""
        if 'articleset' in self.errors:
            # skip check if error in articlesets: cleaned_data['articlesets'] does not exist
            return
        if not (self.cleaned_data.get('articleset_name') or self.cleaned_data.get('articleset')):
            fn = self.cleaned_data.get('upload')
            if fn:
                return fn.basename
        name = self.cleaned_data['articleset_name']
        if not bool(name) ^ bool(self.cleaned_data['articleset']):
            raise forms.ValidationError("Please specify either articleset or articleset_name")
        return name

    def validate(self):
        return self.is_valid()


def _get_encoding(encoding, binary_content):
    if encoding.lower() == "autodetect":
        encoding = chardet.detect(binary_content)["encoding"]
        if encoding == "ascii":
            encoding = "utf-8"
        log.info("Guessed encoding: {encoding}".format(**locals()))
    return encoding


def _open(file, encoding):
    """Open the file in str (unicode) mode, guessing encoding if needed"""
    binary_content = open(file, mode='rb').read(1000)
    encoding = _get_encoding(encoding, binary_content)
    return open(file, encoding=encoding)


def _read(file: UploadedFile, n=None):
    """Read the file, guessing encoding if needed"""
    binary_content = file.read(n)
    encoding = _get_encoding(file.encoding, binary_content)
    return binary_content.decode(encoding)


class UploadScript(ActionForm):
    """
    Base class for Upload Scripts, which are scraper scripts driven by the
    the script input.

    Implementing classes should implement get_fields and parse_file,
    and may provide additional fields in the form_class
    """
    form_class = UploadForm

    @classmethod
    def get_fields(cls, upload: model_UploadedFile) -> Sequence[ArticleField]:
        """
        Return a sequence of ArticleField objects listing the fields in the uploaded file(s)
        """
        return []

    def parse_file(self, file: UploadedFile, _data: Iterable[Any]) -> Iterable[Article]:
        """
        Parse the file into an iterable of Article objects.
        @param file: The file object
        @param _data: Preprocessed data
        @return: An iterable of Article objects.
        """
        raise NotImplementedError()

    @classmethod
    def _preprocess(cls, file: UploadedFile) -> Any:
        """
        Parse the file into an iterable of preprocessed objects.
        Only called if overridden.

        @param file:
        @return:
        """
        raise NotImplementedError()

    @classmethod
    def _get_preprocessed(cls, file: UploadedFile) -> Tuple[UploadedFile, Any]:
        """
        Get and cache _preprocess(file)
        If preprocessing is desired, _preprocess should return a json-serializable object
        @param file: The full filename
        @param encoding: The encoding of the file
        @return: A tuple (file, preprocess_data)
        """
        if not cls.has_preprocess():
            return file, None
        cachefn = file.file.name + "__upload_cache_{}.json".format(cls.__name__)
        log.debug("Cache file {cachefn} exists? {}".format(os.path.exists(cachefn), **locals()))
        if os.path.exists(cachefn):
            data = json.load(open(cachefn))
        else:
            data = cls._preprocess(file)
            json.dump(data, open(cachefn, "w"), cls=DjangoJSONEncoder, indent=2)
        return file, data

    @classmethod
    def has_preprocess(cls):
        return cls._preprocess.__func__ is not UploadScript._preprocess.__func__

    @classmethod
    def _get_files(cls, upload: model_UploadedFile, monitor=NullMonitor()) -> Iterable[Tuple[UploadedFile, Any]]:
        """
        Get the files to upload, unpacking zip files if needed, and returning preprocessed data if applicable
        @param file: Full file path
        @param encoding: The encoding of the file
        @param monitor: A monitor with progress=0, total=100
        @return: An iterable of (file, encoding, preprocessed_data_or_None)
        """
        monitor = monitor.submonitor(len(upload), weight=100)
        monitor.update(0, "Unpacking and preprocessing file(s).")
        for file in upload:
            monitor.update()
            yield cls._get_preprocessed(file)


    def __init__(self, form=None, file=None, **kargs):
        if form is None:
            form = self.form_class(data=kargs, files={"file": file})
        super().__init__(form)
        self.progress_monitor = NullMonitor()
        self.options = self.form.cleaned_data
        self.project = self.options['project']
        self.errors = []

    def get_or_create_articleset(self):
        if self.options['articleset']:
            return self.options['articleset']

        if self.options['articleset_name']:
            aset = create_new_articleset(self.options['articleset_name'], self.project)
            self.options['articleset'] = aset
            return aset

        return ()

    def explain_error(self, error, article=None, index=None):
        """Explain the error in the context of unit for the end user"""
        index = " {}".format(article) if article is not None else ""
        return "Error in element{}: {}".format(index, error)

    def get_provenance(self, file, articles):
        n = len(articles)
        timestamp = str(datetime.datetime.now())[:16]
        return ("[{timestamp}] Uploaded {n} articles from file {file!r} "
                "using {self.__class__.__name__}".format(**locals()))

    def run(self):
        upload = self.options['upload']
        upload.encoding_override(self.options['encoding'])

        monitor = self.progress_monitor

        root_dir = os.path.dirname(upload.filepath)

        monitor.update(10, u"Importing {self.__class__.__name__} from {upload.basename} into {self.project}"
                       .format(**locals()))

        articles = []
        files = self._get_files(upload)
        nfiles = len(upload)
        filemonitor = monitor.submonitor(nfiles, weight=60)
        for i, (file, data) in enumerate(files):
            filemonitor.update(1, "Parsing file {i}/{nfiles}: {file.name}".format(**locals()))
            articles += list(self.parse_file(file, data))

        for article in articles:
            _set_project(article, self.project)

        if self.errors:
            raise ParseError(" ".join(map(str, self.errors)))
        monitor.update(10, "All files parsed, saving {n} articles".format(n=len(articles)))
        Article.create_articles(articles, articleset=self.get_or_create_articleset(),
                                monitor=monitor.submonitor(40))

        if not articles:
            raise Exception("No articles were imported")

        monitor.update(10, "Uploaded {n} articles, post-processing".format(n=len(articles)))

        aset = self.options['articleset']
        new_provenance = self.get_provenance(upload.basename, articles)
        aset.provenance = ("%s\n%s" % (aset.provenance or "", new_provenance)).strip()
        aset.save()

        if getattr(self, 'task', None):
            self.task.log_usage("articles", "upload", n=len(articles))

        monitor.update(10, "Done! Uploaded articles".format(n=len(articles)))
        return self.options["articleset"]

    def map_article(self, art_dict):
        mapped_dict = {}
        for destination, field in self.options['field_map'].items():
            if field['type'] == "field":
                mapped_dict[destination] = art_dict[field["value"]]
            elif field["type"] == "literal":
                mapped_dict[destination] = field["value"]
            else:
                raise Exception("type should be 'field' or 'literal'")
        return mapped_dict



class PreprocessForm(UploadForm):
    upload = forms.ModelChoiceField(model_UploadedFile.objects.all())
    script = forms.ChoiceField(choices=())
    field_map = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from amcat.scripts.article_upload.upload_plugins import get_upload_plugins
        self.fields['script'].choices = [(k, k) for k in get_upload_plugins().keys()]

class PreprocessScript(ActionForm):
    form_class = PreprocessForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_monitor = NullMonitor()

    def _articlefield_as_kwargs(self, article_field: ArticleField):
        return {k: getattr(article_field, k)
             for k in ("label", "suggested_destination", "values", "possible_types", "suggested_type")}


    def run(self):
        from amcat.scripts.article_upload.upload_plugins import get_upload_plugin
        self.progress_monitor.update(0, "Preprocessing files")
        plugin_name = self.form.cleaned_data['script']
        plugin = get_upload_plugin(plugin_name)
        upload = self.form.cleaned_data['upload']
        upload.encoding_override(self.form.cleaned_data['encoding'])
        if plugin.script_cls.has_preprocess():
            filesmonitor = self.progress_monitor.submonitor(100, weight=80)
            for _ in plugin.script_cls._get_files(upload, monitor=filesmonitor):
                pass
        else:
            self.progress_monitor.update(80)
        self.progress_monitor.update(0, "Collecting fields")
        fields = [self._articlefield_as_kwargs(field) for field in
                  plugin.script_cls.get_fields(upload)]

        self.progress_monitor.update(20, "Done")
        return fields

def _set_project(art, project):
    try:
        if getattr(art, "project", None) is not None:
            return
    except Project.DoesNotExist:
        pass  # django throws DNE on x.y if y is not set and not nullable
    art.project = project
