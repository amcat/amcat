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

import chardet

from django.db import transaction
from django import forms

from amcat.scripts import script
from amcat.scripts.types import ArticleIterator
from amcat.models.article import Article
from amcat.scraping.scraper import ScraperForm, Scraper

class ParseError(Exception):
    pass

ENCODINGS = ["Autodetect", "ISO-8859-15", "UTF-8", "Latin-1"]

class UploadForm(ScraperForm):
    encoding = forms.ChoiceField(choices=enumerate(ENCODINGS),
                                 initial=0, required=False, 
                                 help_text="Try to change this value when character issues arise.", )
    file = forms.FileField()

    def clean_articleset_name(self):
        """If article set name not specified, use file base name instead"""
        if self.files['file'] and not (self.cleaned_data['articleset_name'] or self.cleaned_data['articleset']):
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

    def decode(self, bytes):
        """
        Decode the given bytes using the encoding specified in the form.
        If encoding is Autodetect, use (1) utf-8, (2) chardet, (3) latin-1.
        """
        enc = ENCODINGS[int(self.options['encoding'] or 0)]
        if enc != 'Autodetect':
            return bytes.decode(enc)
        try:
            return bytes.decode('utf-8')
        except UnicodeDecodeError:
            pass
        enc = chardet.detect(bytes)["encoding"]
        if enc:
            try:
                return bytes.decode('utf-8')
            except UnicodeDecodeError:
                pass
        return bytes.decode('latin-1')

        
    
    @property
    def input_text(self):
        try:
            return self._input_text
        except AttributeError:
            self._input_text = self.decode(self.options['file'].read())
            return self._input_text

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
        from amcat.scraping.controller import SimpleController
        with transaction.commit_on_success():
            arts = list(SimpleController(self.articleset).scrape(self))

            old_provenance = [] if self.articleset.provenance is None else [self.articleset.provenance]
            new_provenance = self.get_provenance(file, arts)
            self.articleset.provenance = "\n".join([new_provenance] + old_provenance)
            self.articleset.save()
        
        return arts


    def _get_units(self):
        return [self.options['file']]

    def _scrape_unit(self, file):
        documents = self.split_file(file)
        for i, document in enumerate(documents):
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
        return [self.decode(file.read())]
