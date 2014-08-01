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
import os.path
import datetime
import logging
import zipfile
from amcat.forms.widgets import JQueryMultipleSelect

log = logging.getLogger(__name__)

from django import forms
from django.forms.widgets import HiddenInput

from amcat.scripts import script
from amcat.scripts.types import ArticleIterator
from amcat.models import Article, Project, ArticleSet
from amcat.scripts.article_upload.fileupload import RawFileUploadForm
from amcat.models.articleset import create_new_articleset


class ParseError(Exception):
    pass


class UploadForm(RawFileUploadForm):
    project = forms.ModelChoiceField(queryset=Project.objects.all())

    articlesets = forms.ModelMultipleChoiceField(
        queryset=ArticleSet.objects.all(), required=False,
        help_text="If you choose an existing articleset, the articles will be "
        "appended to that set. If you leave this empty, a new articleset will be "
        "created using either the name given below, or using the file name")

    articleset_name = forms.CharField(
        max_length=ArticleSet._meta.get_field_by_name('name')[0].max_length,
        required=False)

    def clean_articleset_name(self):
        """If article set name not specified, use file base name instead"""
        if self.files.get('file') and not (self.cleaned_data.get('articleset_name') or self.cleaned_data.get('articleset')):
            fn = os.path.basename(self.files['file'].name)
            return fn
        name = self.cleaned_data['articleset_name']
        if not bool(name) ^ bool(self.cleaned_data['articlesets']):
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


class UploadScript(script.Script):
    """Base class for Upload Scripts, which are scraper scripts driven by the
    the script input.

    For legacy reasons, parse_document and split_text may be used instead of the standard
    get_units and scrape_unit.
    """

    input_type = None
    output_type = ArticleIterator
    options_form = UploadForm

    def __init__(self, *args, **kargs):
        super(UploadScript, self).__init__(*args, **kargs)
        self.project = self.options['project']
        for k, v in self.options.items():
            if type(v) == str:
                self.options[k] = v.decode('utf-8')

        # avoid django problem/bug with repr(File(open(uncode-string)))
        # https://code.djangoproject.com/ticket/8156
        o2 = {k:v for k,v in self.options.iteritems() if k != 'file'}
        log.debug(u"Articleset: {self.articlesets!r}, options: {o2}"
                  .format(**locals()))

    @property
    def articleset(self):
        return self.articlesets[0]

    @property
    def articlesets(self):
        if self.options['articlesets']:
            return self.options['articlesets']

        if self.options['articleset_name']:
            aset = create_new_articleset(self.options['articleset_name'], self.project)
            self.options['articlesets'] = (aset,)
            return (aset,)

        return ()

    def get_errors(self):
        """return a list of document index, message pairs that explains encountered errors"""
        try:
            errors = self.controller.errors
        except AttributeError:
            log.exception("Cannot get controller errors")
            return

        for error in errors:
            yield self.explain_error(error)

    def explain_error(self, error):
        """Explain the error in the context of unit for the end user"""
        return "Error in element {error.i} : {error.error!r}".format(**locals())

    def decode(self, bytes):
        """Decode the bytes using the encoding from the form"""
        enc, text = self.bound_form.decode(bytes)
        return text

    @property
    def uploaded_texts(self):
        """A cached sequence of UploadedFile objects"""
        try:
            return self._input_texts
        except AttributeError:
            self._input_texts = self.bound_form.get_uploaded_texts()
            return self._input_texts

    def get_provenance(self, file, articles):
        n = len(articles)
        filename = file and file.name
        timestamp = unicode(datetime.datetime.now())[:16]
        return ("[{timestamp}] Uploaded {n} articles from file {filename!r} "
                "using {self.__class__.__name__}".format(**locals()))

    def run(self, _dummy=None):
        file = self.options['file']
        filename = file and file.name
        log.info(u"Importing {self.__class__.__name__} from {filename} into {self.project}"
                 .format(**locals()))
        from amcat.scripts.article_upload.controller import Controller
        self.controller = Controller()
        arts = self.controller.run(self)

        if not arts:
            raise Exception("No articles were imported")

        self.postprocess(arts)

        for aset in self.articlesets:
            new_provenance = self.get_provenance(file, arts)
            aset.provenance = ("%s\n%s" % (aset.provenance or "", new_provenance)).strip()
            aset.save()

        return [aset.id for aset in self.articlesets]

    def postprocess(self, articles):
        """
        Optional postprocessing of articles. Removing aricles from the list will exclude them from the
        article set (if needed, list should be changed in place)
        """
        pass

    def _get_units(self):
        """
        Upload form assumes that the form (!) has a get_entries method, which you get
        if you subclass you form from one of the fileupload forms. If not, please override
        this method.
        """
        for entry in self.bound_form.get_entries():
            for u in self.split_file(entry):
                yield u

    def _scrape_unit(self, document):
        result =  self.parse_document(document)
        if isinstance(result, Article):
            result = [result]
        for art in result:
            yield art

    def parse_document(self, document):
        """
        Parse the document as one or more articles, provided for legacy purposes

        @param document: object received from split_text, e.g. a string fragment
        @return: None, an Article or a sequence of Article(s)
        """
        raise NotImplementedError()

    def split_file(self, file):
        """
        Split the file into one or more fragments representing individual documents.
        Default implementation returns a single fragment containing the unicode text.

        @type file: file like object
        @return: a sequence of objects (e.g. strings) to pass to parse_documents
        """
        return [file]

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
from amcat.tools import amcatlogging
amcatlogging.debug_module("amcat.scripts.article_upload.upload")

class TestUpload(amcattest.AmCATTestCase):
    def todo_test_zip_file(self):
        from tempfile import NamedTemporaryFile
        from django.core.files import File
        # does _get_units perform normally
        with NamedTemporaryFile(prefix=u"upload_test", suffix=".txt") as f:
            f.write("Test")
            f.flush()
            s = UploadScript(project=amcattest.create_test_project().id,
                             file=File(f))
            self.assertEqual({u.name for u in s._get_units()}, {f.name})

        # does a zip file work?

            #handle, fn = mkstemp(suffix=".zip")
        with NamedTemporaryFile(suffix=".zip") as f:
            with zipfile.ZipFile(f,  "w") as zf:
                zf.writestr("test.txt", "TEST")
                zf.writestr("x/test.txt", "TAST")

            s = UploadScript(project=amcattest.create_test_project().id,
                             file=File(f))
            self.assertEqual({f.name for f in s._get_units()}, {"test.txt", "x/test.txt"})
            self.assertEqual({f.read() for f in s._get_units()}, {"TEST", "TAST"})
