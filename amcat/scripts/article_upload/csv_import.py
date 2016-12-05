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
Plugin for uploading csv files
"""
import csv
import datetime
import logging
import itertools
from collections import defaultdict
from io import TextIOWrapper

from amcat.models import Article, get_property_primitive_type
from amcat.scripts.article_upload.upload import UploadScript, ParseError, ARTICLE_FIELDS, ArticleField
from amcat.tools.toolkit import read_date

log = logging.getLogger(__name__)

REQUIRED = tuple(
    field.name for field in Article._meta.get_fields() if field.name in ARTICLE_FIELDS and not field.blank)

TYPES = {
    "date": datetime.datetime,
    "_default": str
}

PARSERS = {
    datetime.datetime: read_date,
    int: int,
    str: str,
    float: float
}


def get_required():
    return REQUIRED


def get_fields():
    return ARTICLE_FIELDS


def get_field_type(field):
    return TYPES.get(field, TYPES['_default'])


def get_parser(field_type):
    return PARSERS.get(field_type, lambda x: x)


class CSV(UploadScript):
    """
    Upload CSV files to AmCAT.

    To tell AmCAT which columns from the csv file to use, you need to specify the name in the file
    for the AmCAT-fields that you want to import. So, if you have a 'title' column in the csv file
    that you want to import as the headline, specify 'title' in the "headline field" input box.

    Text and date and required, all other fields are optional.

    If you are encountering difficulties, please make sure that you know how the csv is exported, and
    manually set encoding and dialect in the options above.

    Since Excel has quite some difficulties with exporting proper csv, it is often better to use
    an alternative such as OpenOffice or Google Spreadsheet (but see below for experimental xlsx support).
    If you must use excel, there is a 'tools' button on the save dialog which allows you to specify the
    encoding and delimiter used.

    We have added experimental support for .xlsx files (note: only use .xlsx, not the older .xls file type).
    This will hopefully alleviate some of the problems with reading Excel-generated csv file. Only the
    first sheet will be used, and please make sure that the data in that sheet has a header row. Please let
    us know if you encounter any difficulties at github.com/amcat/amcat/issues. Since you can only attach
    pictures there, the best way to share the file that you are having difficulty with (if it is not private)
    is to upload it to dropbox or a file sharing website and paste the link into the issue.
    """

    _errors = {
        "empty_col": 'Expected non-empty value in table column "{}" for required field "{}".',
        "empty_val": 'Expected non-empty value for required field "{}".',
        "parse_value": 'Failed to parse value "{}". Expected type: {}.'
    }

    def run(self, *args, **kargs):
        return super(CSV, self).run(*args, **kargs)

    def parse_value(self, property, value):
        t = get_property_primitive_type(property)
        parser = PARSERS[t]
        return parser(value)

    def parse_file(self, file):
        file_name = file.name
        reader = csv.DictReader(TextIOWrapper(file.file, encoding="utf8"))
        for unmapped_dict in reader:
            art_dict = self.map_article(unmapped_dict)
            properties = {}
            for k, v in art_dict.items():
                v = self.parse_value(k, v)
                properties[k] = v
            yield Article.fromdict(properties)

    def split_file(self, file):
        for reader in file:
            yield reader

    def explain_error(self, error, article=None):
        return "Error in row {}: {}".format(article, error)

    @classmethod
    def get_fields(cls, file, encoding):
        for f in UploadScript.unpack_file(file):
            reader = csv.DictReader(TextIOWrapper(f.file, encoding="utf-8"))
            values = list(itertools.islice(reader, 0, 5))
            known_articleset_fields = set() #TODO: get these somehow
            known_fields = set(ARTICLE_FIELDS) | known_articleset_fields

            for column in reader.fieldnames:
                article_field = ArticleField(column)
                if column.lower() in known_fields:
                    article_field.suggested_destination = column.lower()
                article_field.values = [v[column] for v in values]

                yield article_field

    def map_article(self, art_dict):
        mapped_dict = {}
        field_map = self.options['field_map']["fields"]
        for k, v in art_dict.items():
            try:
                dest = field_map[k]
            except KeyError:
                pass
            else:
                mapped_dict[dest] = v
        for k, v in self.options['field_map']["literals"].items():
            mapped_dict[k] = v
        return mapped_dict

if __name__ == '__main__':
    from amcat.scripts.tools import cli

    cli.run_cli(CSV)
