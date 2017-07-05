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
from collections import OrderedDict
from typing import Any, Iterable, Mapping, Sequence, Tuple

import chardet
from actionform import ActionForm
from django import forms
from django.contrib.postgres.forms import JSONField
from django.core.files.utils import FileProxyMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.widgets import HiddenInput

from amcat.models import Article, ArticleSet, Project
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

    def __init__(self, label, destination=None, values=None, possible_types=None, suggested_type=None):
        self.label = label  # name in uploaded file
        self.suggested_destination = destination  # suggested destination model field
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
    filename = forms.CharField()
    project = forms.ModelChoiceField(queryset=Project.objects.all())

    articleset = forms.ModelChoiceField(
        queryset=ArticleSet.objects.all(), required=False,
        help_text="If you choose an existing articleset, the articles will be "
                  "appended to that set. If you leave this empty, a new articleset will be "
                  "created using either the name given below, or using the file name")

    articleset_name = forms.CharField(
        max_length=ArticleSet._meta.get_field('name').max_length,
        required=False)

    encoding = forms.ChoiceField(choices=[(x, x) for x in ["Autodetect", "ISO-8859-15", "UTF-8", "Latin-1"]])
    field_map = JSONField(validators=[validate_field_map],
                          help_text='json dict with property names (title, date, etc.) as keys, and field settings as values. '
                                    'Field settings should have the form {"type": "field"/"literal", "value": "field_name_or_literal"}')

    def clean_articleset_name(self):
        """If articleset name not specified, use file base name instead"""
        if 'articleset' in self.errors:
            # skip check if error in articlesets: cleaned_data['articlesets'] does not exist
            return
        if not (self.cleaned_data.get('articleset_name') or self.cleaned_data.get('articleset')):
            fn = self.cleaned_data.get('filename')
            if (not fn) and self.cleaned_data.get('file'):
                fn = self.cleaned_data.get('file').name
            if fn:
                return os.path.basename(fn)
        name = self.cleaned_data['articleset_name']
        if not bool(name) ^ bool(self.cleaned_data['articleset']):
            raise forms.ValidationError("Please specify either articleset or articleset_name")
        return name

    @classmethod
    def get_empty(cls, project=None, post=None, files=None, **_options):
        f = cls(post, files) if post is not None else cls()
        if project:
            f.fields['project'].initial = project.id
            f.fields['project'].widget = HiddenInput()
            f.fields['articlesets'].queryset = ArticleSet.objects.filter(project=project)
        return f

    def validate(self):
        return self.is_valid()

def _open(file, encoding):
    """Open the file in str (unicode) mode, guessing encoding if needed"""
    if encoding.lower() == 'autodetect':
        bytes = open(file, mode='rb').read(1000)
        encoding = chardet.detect(bytes)["encoding"]
        log.info("Guessed encoding: {encoding}".format(**locals()))
    return open(file, encoding=encoding)

def _read(file, encoding, n=None):
    """Read the file, guessing encoding if needed"""
    bytes = open(file, mode='rb').read(n)
    if encoding.lower() == 'autodetect':
        encoding = chardet.detect(bytes[:1000])["encoding"]
        log.info("Guessed encoding: {encoding}".format(**locals()))
    return bytes.decode(encoding)


class UploadScript(ActionForm):
    """
    Base class for Upload Scripts, which are scraper scripts driven by the
    the script input.

    Implementing classes should implement get_fields and parse_file,
    and may provide additional fields in the form_class
    """
    form_class = UploadForm

    @classmethod
    def get_fields(cls, file: str, encoding: str) -> Sequence[ArticleField]:
        """
        Return a sequence of ArticleField objects listing the fields in the uploaded file(s)
        """
        return []

    def parse_file(self, file: str, encoding: str, _data) -> Iterable[Article]:
        """
        Parse the file into an iterable of Article objects.
        @param file: The full file path
        @param encoding: The encoding of the file
        @param _data: Preprocessed data
        @return: An iterable of Article objects.
        """
        raise NotImplementedError()

    @classmethod
    def _get_preprocessed(cls, file: str, encoding: str) -> Tuple[str, str, Any]:
        """
        Get and cache _preprocess(file, encoding)
        If preprocessing is desired, _preprocess should return a json-serializable object
        @param file: The full filename
        @param encoding: The encoding of the file
        @return: A tuple (file, encoding, preprocess_data)
        """
        if not hasattr(cls, "_preprocess"):
            return file, encoding, None
        cachefn = file + "__upload_cache.json"
        log.debug("Cache file {cachefn} exists? {}".format(os.path.exists(cachefn), **locals()))
        if os.path.exists(cachefn):
            data = json.load(open(cachefn))
        else:
            data = cls._preprocess(file, encoding)
            json.dump(data, open(cachefn, "w"), cls=DjangoJSONEncoder, indent=2)
        return file, encoding, data

    @classmethod
    def _get_files(cls, file: str, encoding: str) -> Iterable[Tuple[str, str, Any]]:
        """
        Get the files to upload, unpacking zip files if needed, and returning preprocessed data if applicable
        @param file: Full file path
        @param encoding: The encoding of the file
        @return: An iterable of (file, encoding, preprocessed_data_or_None)
        """
        if file.endswith(".zip"):
            path = os.path.dirname(file)
            zf = zipfile.ZipFile(file)
            for member in zf.namelist():
                if member.endswith('/'):
                    continue
                fn = os.path.join(path, member)
                if not os.path.exists(fn):
                    zf.extract(member, path=path)
                yield cls._get_preprocessed(fn, encoding)
        else:
            yield cls._get_preprocessed(file, encoding)

    def __init__(self, form=None, file=None, **kargs):
        if form is None:
            form = self.form_class(data=kargs, files={"file": file})
        super().__init__(form)
        self.progress_monitor = NullMonitor()
        self.options = self.form.cleaned_data
        self.project = self.form.cleaned_data['project']
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
        monitor = self.progress_monitor

        filename = self.options['filename']
        file_shortname = os.path.split(self.options['filename'])[-1]
        monitor.update(10, u"Importing {self.__class__.__name__} from {file_shortname} into {self.project}"
                       .format(**locals()))

        articles = []
        encoding = self.options['encoding']
        files = list(self._get_files(filename, encoding))
        nfiles = len(files)
        for i, (file, encoding, data) in enumerate(files):
            monitor.update(20 / nfiles, "Parsing file {i}/{nfiles}: {file}".format(**locals()))
            articles += list(self.parse_file(file, encoding, data))

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

        aset = self.options["articleset"]
        new_provenance = self.get_provenance(file, articles)
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


def _set_project(art, project):
    try:
        if getattr(art, "project", None) is not None:
            return
    except Project.DoesNotExist:
        pass  # django throws DNE on x.y if y is not set and not nullable
    art.project = project
