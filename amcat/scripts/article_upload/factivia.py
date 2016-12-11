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
import collections
from lxml import html

from amcat.models import Article
from amcat.scripts.article_upload.upload import UploadScript, ArticleField
from amcat.tools.toolkit import read_date

META = ["title", "length", "date", "medium", None, "page"]


def split_file(file):
    # Parses HTML file (bytes) to a more convienient lxml representation
    document = html.fromstring(file.read())

    # Selects all elements with class=article
    return document.cssselect(".article")


def parse_doc(document):
    # We select all 'div' elements directly under '.article'
    divs = document.cssselect("* > div")

    # Check for author field. If present: remove from metadata
    # fields list
    try:
        author_field = document.cssselect(".author")[0]
    except IndexError:
        pass
    else:
        yield "author", author_field.text_content().lstrip("Von").strip()
        divs.remove(author_field)

    # Strip everything before headline
    headline_field = document.cssselect("b.deHeadline")[0].getparent()
    divs = divs[divs.index(headline_field):]

    # Parse metadata. Loop through each 'div' within an article, along with
    # its field name according to META (thus based on its position)
    for field_name, element in zip(META, divs):
        if field_name is None:
            continue

        value = element.text_content().strip()
        if field_name == "length":
            value = int(value.rstrip("words"))
        elif field_name == "date":
            value = read_date(value)
            # WVA: WAS: raise NotImplemented("Parse date here: do not use toolkit.read_date")... why?
        elif field_name == "page":
            if value.strip().isdigit():
                value = int(value.strip())
            else:
                continue

        yield field_name, value

    # Fetch text, which is
    paragraphs = [p.text_content() for p in document.cssselect("p")]
    yield "text", ("\n\n".join(paragraphs)).strip()


class Factivia(UploadScript):
    @classmethod
    def get_fields(cls, file, encoding):
        fields = collections.OrderedDict()
        for doc in split_file(file):
            for k, v in parse_doc(doc):
                fields[k] = fields.get(k, []) + [v]
        return [ArticleField(k, k, values) for (k, values) in fields.items()]

    def parse_file(self, file):
        for doc in split_file(file):
            data = dict(parse_doc(doc))

            art = {}
            for field, setting in self.options['field_map'].items():
                value, typ = setting['value'], setting['type']
                val = data.get(value) if typ == 'field' else value
                if val:
                    art[field] = val
            yield Article(**art)





