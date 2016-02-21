# ##########################################################################
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
A PDF parser
"""

from pdfminer.pdfparser import PDFParser as module_parser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTFigure

import logging
log = logging.getLogger(__name__)


class PDFParser(object):
    def load_document(self, _file, password=""):
        """turn the file into a PDFMiner document"""
        log.info("loading document...")
        
        parser = module_parser(_file)
        doc = PDFDocument(parser, password)


        if not doc.is_extractable:
            raise ValueError("PDF text extraction not allowed")

        return doc

    def process_page(self, page, params=None):
        """processes a page using the parameters given
        params should be passed in a dictionary, and are named as follows:
            char_margin 
            line_margin
            word_margin
        (see http://www.unixuser.org/~euske/python/pdfminer/)
        returns: a LTPage object
        (see http://www.unixuser.org/~euske/python/pdfminer/programming.html)
        """
        if params:
            params = LAParams(**params)
        resourcemanager = PDFResourceManager()
        device = PDFPageAggregator(resourcemanager, laparams=params)
        interpreter = PDFPageInterpreter(resourcemanager, device)

        interpreter.process_page(page)
        return device.get_result()

    def process_document(self, doc, params=None):
        for i, page in enumerate(PDFPage.create_pages(doc)):
            log.info("processing page {i}".format(**locals()))
            yield self.process_page(page, params)

    def parse_layout(self, objects):
        result = []
        for obj in objects:
            if 'get_text' in dir(obj):
                text = obj.get_text()
                print(text)
            if isinstance(obj, LTTextBox) or isinstance(obj, LTTextLine):
                result.append(obj.get_text())
            elif isinstance(obj, LTFigure):
                result.append(self.parse_layout(obj._objs))
        return result

    def get_textlines(self, page, params=None):
        if not params:
            params = {}
        if not isinstance(params, LAParams):
            params = LAParams(**params)
        objects = [o for o in page._objs if hasattr(o, 'is_compatible')]
        for line in page.group_objects(params, objects):
            yield line

    def get_textboxes(self, page, params=None):
        if not params:
            params = {}
        if not isinstance(params, LAParams):
            params = LAParams(**params)
        lines = self.get_textlines(page, params)
        for textbox in page.get_textboxes(params, list(lines)):
            yield textbox
