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
log = logging.getLogger(__name__)

from django.db import transaction
from django import forms
from django.core.files import File

from amcat.scripts import script
from amcat.scripts.types import ArticleIterator
from amcat.models.article import Article
from amcat.scraping.scraper import ScraperForm, Scraper

from amcat.scripts.article_upload.fileupload import RawFileUploadForm

class ParseError(Exception):
    pass
    
class UploadForm(ScraperForm, RawFileUploadForm):
    def clean_articleset_name(self):
        """If article set name not specified, use file base name instead"""
        if self.files.get('file') and not (self.cleaned_data.get('articleset_name') or self.cleaned_data.get('articleset')):
            fn = os.path.basename(self.files['file'].name)
            return fn
        return super(UploadForm, self).clean_articleset_name()
    
class UploadScript(Scraper):
    """Base class for Upload Scripts, which are scraper scripts driven by the
    the script input.

    For legacy reasons, parse_document and split_text may be used instead of the standard
    get_units and scrape_unit.
    """
    
    input_type = None
    output_type = ArticleIterator
    options_form = UploadForm

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
        filename = file.name
        timestamp = unicode(datetime.datetime.now())[:16]
        return ("[{timestamp}] Uploaded {n} articles from file {filename!r} "
                "using {self.__class__.__name__}".format(**locals()))
        
    def run(self, _dummy=None):
        file = self.options['file']
        log.info(u"Importing {self.__class__.__name__} from {file.name} into {self.project}"
                 .format(**locals()))
        from amcat.scraping.controller import RobustController
        self.controller = RobustController(self.articleset)
        with transaction.commit_on_success():
            arts = list(self.controller.scrape(self))
            if not arts:
                raise Exception("No atricles were imported")
            self.postprocess(arts)
            old_provenance = [] if self.articleset.provenance is None else [self.articleset.provenance]
            new_provenance = self.get_provenance(file, arts)
            self.articleset.provenance = "\n".join([new_provenance] + old_provenance)
            self.articleset.save()

        return arts

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

        @type text: unicode string
        @return: a sequence of objects (e.g. strings) to pass to parse_documents
        """
        return [file]

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
from amcat.tools import amcatlogging
amcatlogging.debug_module("amcat.scripts.article_upload.upload")

class TestUpload(amcattest.PolicyTestCase):
    def test_zip_file(self):
        from tempfile import NamedTemporaryFile, mkstemp
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

