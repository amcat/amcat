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
Plugin for uploading any pdf file as raw text
"""


from django import forms
from datetime import date

from amcat.scripts.article_upload.upload import UploadScript, UploadForm
from amcat.scripts.article_upload.pdf import PDFParser
from amcat.models.article import Article
from amcat.models.medium import Medium

class RawPDFForm(UploadForm):
    pdf_password = forms.CharField(required = False)
    medium = forms.ModelChoiceField(queryset=Medium.objects.all())
    headline = forms.CharField(required=False, help_text='If left blank, use filename (without extension and optional date prefix) as headline')
    date = forms.DateField(required=False, help_text='If left blank, use current date')
    section = forms.CharField(required=False)

class RawPDFScraper(UploadScript):
    options_form = RawPDFForm
    def _scrape_unit(self, _file):
        """unit: a pdf document"""
        res = ""
        parser = PDFParser()
        doc = parser.load_document(_file, self.options['pdf_password'])
        for page in parser.process_document(doc):
            page_txt = ""
            for line in parser.get_textlines(page):
                page_txt += line.get_text() + "\n"
            res += page_txt + "\n\n"
        article = Article(text = res)
        article.headline = self.getheadline(_file)
        article.medium = self.options['medium']
        article.section = self.options['section']
        if self.options['date']:
            article.date = self.options['date']
        else:
            article.date = date.today()
        yield article

    def getheadline(self, _file):
        hl = _file.name
        if hl.endswith(".pdf"): hl = hl[:-len(".pdf")]
        windows = hl.split("\\")
        other = hl.split("/")
        if len(windows) > len(other):
            #probably a windows path
            hl = windows[-1]
        else:
            hl = other[-1]
        return hl

if __name__ == "__main__":
    from amcat.scripts.tools import cli
    cli.run_cli(RawPDFScraper)
        
            
