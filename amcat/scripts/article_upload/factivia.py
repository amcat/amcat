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

from lxml import html

from amcat.models import Article
from amcat.scripts.article_upload.upload import UploadScript

META = ["headline", "length_int", "date", "medium", None, "page_int"]


class Factivia(UploadScript):
    def split_file(self, file):
        # Parses HTML file (bytes) to a more convienient lxml representation
        document = html.fromstring(file.read())

        # Selects all elements with class=article
        return document.cssselect(".article")

    def _scrape_unit(self, document):
        article = Article()
        metadata = list(META)

        # We select all 'div' elements directly under '.article'
        divs = document.cssselect("* > div")

        # Check for author field. If present: remove from metadata
        # fields list
        try:
            author_field = document.cssselect(".author")[0]
        except IndexError:
            pass
        else:
            article.author = author_field.text_content().lstrip("Von").strip()
            divs.remove(author_field)

        # Strip everything before headline
        headline_field = document.cssselect("b.deHeadline")[0].getparent()
        divs = divs[divs.index(headline_field):]

        # Parse metadata. Loop through each 'div' within an article, along with
        # its field name according to META (thus based on its position)
        for field_name, element in zip(metadata, divs):
            if field_name is None:
                continue

            value = element.text_content().strip()
            if field_name == "length":
                value = int(value.rstrip("words"))
            elif field_name == "date":
                raise NotImplemented("Parse date here: do not use toolkit.read_date")
            elif field_name == "page_int":
                if p.strip().isdigit():
                    value = int(p.strip())
                else:
                    continue

            article.set_property(field_name, value)

        # Fetch text, which is
        paragraphs = [p.text_content() for p in document.cssselect("p")]
        article.text = ("\n\n".join(paragraphs)).strip()

        # We must return a iterable, so we return a one-tuple
        return (article,)

