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
Configuration options to change how AmCAT uses elastic
"""
import datetime
import os
import sys

from settings.tools import get_amcat_config
amcat_config = get_amcat_config()

TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

# Host/port on which elastic can be reached:
ES_HOST = amcat_config["elasticsearch"].get("host")
ES_PORT = amcat_config["elasticsearch"].get("port")
ES_INDEX = amcat_config["elasticsearch"].get("index")

if TESTING:
    # Emulate Django behaviour by prepending index name with 'test_' if running
    ES_INDEX = "test_{}".format(ES_INDEX)

ES_ARTICLE_DOCTYPE = 'article'


ES_MAPPING_TYPE_PRIMITIVES = {
    "int": int,
    "date": datetime.datetime,
    "num": float,
    "url": str,
    "id": str,
    "text": str,
    "default": str,
    "tag": set,
}


ES_MAPPING_TYPES = {
    'int': {"type": "long"},
    'date': {"format": "dateOptionalTime", "type": "date"},
    'num': {"type": "double"},
    'url': {"type": "keyword"},
    'id': {"type": "keyword"},
    'text': {"type": "text"},
    'tag': {"type": "text", "analyzer": "tag"},
    'default': {"type": "text",
                 "fields": {"raw":   { "type": "keyword", "ignore_above": 256}}}
    }

ES_MAPPING = {
    "properties": {
        # id / hash / project/set membership
        "id": ES_MAPPING_TYPES['int'],
        "sets": ES_MAPPING_TYPES['int'],
        "hash": ES_MAPPING_TYPES['id'],
        "parent_hash": ES_MAPPING_TYPES['id'],
        # article properties
        "date": ES_MAPPING_TYPES['date'],
        "title": ES_MAPPING_TYPES['default'],
        "url": ES_MAPPING_TYPES['url'],
        "text": ES_MAPPING_TYPES['text'],
    },
}

ES_SETTINGS = {
    "index": {
      "similarity": {
        "default": {
          "type": "hitcountsimilarity"
        }
      }
    },
    "analysis": {
        "analyzer": {
            "default": {
                "type": "custom",
                "tokenizer": "unicode_letters_digits",
                "filter": [
                    "icu_folding", "lengthfilter"
                ],
            },
            "tag": {
                "type": "pattern",
                "pattern": "\s*,\s*",
            },
        },
        "tokenizer": {
            "unicode_letters_digits": {
                "type": "pattern",
                "pattern": "[^\\p{L}\\p{M}\\p{N}]",
                "lowercase": "true"
            }
        },
        # prevent 'immense term' error when people use really long words
        "filter": {
            "lengthfilter": {
                "type": "length",
                "min": 0,
                "max": 2000,
            }
        }
    },
}


