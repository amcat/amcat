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
import logging
import os.path
from typing import Tuple

from django import forms
from django.contrib.postgres.forms import JSONField
from django.forms.widgets import HiddenInput

from amcat.models import Article, Project, ArticleSet
from amcat.models.articleset import create_new_articleset

from actionform import ActionForm

log = logging.getLogger(__name__)

ARTICLE_FIELDS = ("text", "title", "url", "date", "parent_hash")

class ParseError(Exception):
    pass 


class UploadForm(forms.Form):
    file = forms.FileField(help_text="Uploading very large files can take a long time. If you encounter timeout problems, consider uploading smaller files")
    
    project = forms.ModelChoiceField(queryset=Project.objects.all())

    articleset = forms.ModelChoiceField(
        queryset=ArticleSet.objects.all(), required=False,
        help_text="If you choose an existing articleset, the articles will be "
                  "appended to that set. If you leave this empty, a new articleset will be "
                  "created using either the name given below, or using the file name")

    articleset_name = forms.CharField(
        max_length=ArticleSet._meta.get_field_by_name('name')[0].max_length,
        required=False)

    encoding = forms.ChoiceField(choices=[(x,x) for x in ["Autodetect", "ISO-8859-15", "UTF-8", "Latin-1"]])
    field_map = JSONField()

    def clean_articleset_name(self):
        """If articleset name not specified, use file base name instead"""
        if 'articleset' in self.errors:
            #skip check if error in articlesets: cleaned_data['articlesets'] does not exist
            return
        if self.files.get('file') and not (
                    self.cleaned_data.get('articleset_name') or self.cleaned_data.get('articleset')):
            fn = os.path.basename(self.files['file'].name)
            return fn
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

    def get_files(self):
        yield self.cleaned_data['file']

    def validate(self):
        return self.is_valid()
    
class UploadScript(ActionForm):
    """Base class for Upload Scripts, which are scraper scripts driven by the
    the script input.

    Implementing classes should implement get_fields and parse_file,
    and may provide additional fields in the form_class
    """
    form_class = UploadForm

    @classmethod
    def get_fields(cls, file, encoding):
        """
        Returns a dict, containing at least all fields as keys, and a suggested mapping or None as values.
        """
        return {}
    
    def parse_file(self, file):
        raise NotImplementedError()
    
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.options = self.form.cleaned_data
        self.project = self.form.cleaned_data['project']
        self.errors = []

    def get_or_create_articleset(self):
        if self.options['articleset']:
            return self.options['articleset']

        if self.options['articleset_name']:
            aset = create_new_articleset(self.options['articleset_name'], self.project)
            self.options['articleset'] = (aset,)
            return (aset,)

        return ()

    def explain_error(self, error, article=None, index=None):
        """Explain the error in the context of unit for the end user"""
        index = " {}".format(article) if article is not None else ""
        return "Error in element{}: {}".format(article, error)

    def get_provenance(self, file, articles):
        n = len(articles)
        filename = file and file.name
        timestamp = str(datetime.datetime.now())[:16]
        return ("[{timestamp}] Uploaded {n} articles from file {filename!r} "
                "using {self.__class__.__name__}".format(**locals()))

    def run(self):
        monitor = self.progress_monitor

        file = self.options['file']
        filename = file and file.name
        monitor.update(10, u"Importing {self.__class__.__name__} from {filename} into {self.project}"
                       .format(**locals()))

        articles = []

        files = list(self._get_files())
        nfiles = len(files)
        for i, f in enumerate(files):
            filename = getattr(f, 'name', str(f))
            monitor.update(20 / nfiles, "Parsing file {i}/{nfiles}: {filename}".format(**locals()))
            articles += list(self.parse_file(f))

        for article in articles:
            _set_project(article, self.project)
        
        if self.errors:
            raise ParseError(" ".join(map(str, self.errors)))
        monitor.update(10, "All files parsed, saving {n} articles".format(n=len(articles)))
        Article.create_articles(articles, articlesets=self.get_or_create_articleset(),
                                monitor=monitor.submonitor(40))

        if not articles:
            raise Exception("No articles were imported")

        monitor.update(10, "Uploaded {n} articles, post-processing".format(n=len(articles)))

        for aset in self.articlesets:
            new_provenance = self.get_provenance(file, articles)
            aset.provenance = ("%s\n%s" % (aset.provenance or "", new_provenance)).strip()
            aset.save()

        if getattr(self, 'task', None):
            self.task.log_usage("articles", "upload", n=len(articles))

        monitor.update(10, "Done! Uploaded articles".format(n=len(articles)))
        return [a.id for a in self.articlesets]

    def _get_files(self):
        return self.form.get_files()


def _set_project(art, project):
    try:
        if getattr(art, "project", None) is not None: return
    except Project.DoesNotExist:
        pass  # django throws DNE on x.y if y is not set and not nullable
    art.project = project
