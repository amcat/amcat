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
Migrate db from 3.4 (fixed 'newspaper' fields) to 3.5 ('flexible fields')

The DB migration will be in place:
- create/rename new fields (properties, hash, title)
- copy old fields to properties
- optionally drop old fields (will cause 3.4 to stop working)

Note that this requires django-bulk-update

After this, you should probably tell django that the initial migration is done: 
python -m amcat.manage migrate --fake amcat 0001
python -m amcat.manage migrate --fake amcat 0002
And re-index the elasticsearch index
"""

import sys
import logging
import binascii
import csv
import io
import json

import psycopg2

from django.core.management import BaseCommand
from django.db import connection
from django.db import models

from bulk_update.helper import bulk_update

from amcat.tools import amcates
from amcat.models import Article
from amcat.tools.model import PostgresNativeUUIDField

NEW_FIELDS = {"hash": "bytea", "parent_hash": "bytea", "properties" : "jsonb", "title": "text"}

PROP_FIELDS = {"section": models.CharField,
               "pagenr": models.IntegerField,
               "byline": models.TextField,
               "length": models.IntegerField,
               "metastring": models.TextField,
               "externalid": models.IntegerField,
               "author": models.TextField,
               "addressee": models.TextField,
               "uuid": PostgresNativeUUIDField}

class Command(BaseCommand):
    
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('articles', help="CSV file containing the articles dump")
        parser.add_argument('media', help="CSV file containing the media dump")
        parser.add_argument('--no_data', action='store_true', help="Don't copy the date to property fields")
        parser.add_argument('--drop_columns', action='store_true', help="Drop the unneeded columns after migrating")
        
    def handle(self, *args, **options):
        self.drop_old()
        self.create_article_table()
        media = dict(self.get_media(options['media']))
        self.copy_data(options['articles'], media)
        self.create_constraints()

    def get_media(self, fn):
        for line in csv.DictReader(open(fn)):
            yield int(line['medium_id']), line['name']
        
    def drop_old(self):
        logging.info("Dropping contraints")
        with connection.cursor() as c:
            c.execute("""
SELECT
    kcu.table_name, tc.constraint_name
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
WHERE constraint_type = 'FOREIGN KEY' AND ccu.table_name='articles'""")
            constraints = list(c.fetchall())
        for table, constraint in constraints:
            with connection.cursor() as c:
                logging.info(constraint)
                c.execute('ALTER TABLE {table} DROP CONSTRAINT "{constraint}"'.format(**locals()))
        logging.info("Dropping articles table")
        with connection.cursor() as c:
            c.execute("DROP TABLE IF EXISTS articles")
                    
    def create_article_table(self):
        with connection.cursor() as c:
            c.execute('''
            CREATE TABLE "articles" ("article_id" serial NOT NULL PRIMARY KEY, "date" timestamp with time zone NOT NULL, "title" text NOT NULL, "url" text NULL, "text" text NOT NULL, "hash" bytea NOT NULL, "parent_hash" bytea NULL, "properties" jsonb NULL, "project_id" integer NOT NULL);''')
        
    def copy_data(self, fn, media):

        csv.field_size_limit(sys.maxsize)

        cursor = connection.cursor()

        r = csv.reader(open(fn))
        header = next(r)

        buffer = []
        for line in r:
            buffer.append(line)
            if len(buffer) > 1000:
                self.do_copy_data(header, buffer, media)
                buffer = []
        if buffer:
            self.do_copy_data(header, buffer, media)
        #TODO! Deal with parent_hash
            
    def do_copy_data(self, header, data, media):
        logging.info("Copying {} rows".format(len(data)))

        out = io.StringIO()
        outw = csv.writer(out, quoting=csv.QUOTE_ALL)
        
        index = {col: i for (i, col) in enumerate(header)}
        for row in data:
            aid = row[index['article_id']]
            a = Article(
                project_id = row[index['project_id']],
                date = row[index['date']],
                title = row[index['headline']],
                url = row[index['url']],
                text = row[index['text']])
            if not a.text:
                a.text = ""
            
            a.properties = {v: row[index[v]] for v in PROP_FIELDS if row[index[v]]}
            a.properties['medium'] = media[int(row[index['medium_id']])]
            a.properties['uuid'] = str(a.properties['uuid'])
            
            hash = amcates.get_article_dict(a)['hash']
            parent_id = row[index['parent_article_id']]

            # convert hash to postgres binary format
            hash = binascii.unhexlify(hash)
            hash = str(psycopg2.Binary(hash))
            hash = hash[1:-8]
            outw.writerow([a.project_id, aid, a.date, a.title, a.url, a.text, hash, json.dumps(a.properties)])

        out.seek(0)
        with connection.cursor() as c:
            cols = ", ".join(['project_id', 'article_id', 'date', 'title', 'url', 'text', 'hash', 'properties'])
            sql = "COPY articles ({cols}) FROM STDIN WITH (FORMAT CSV)".format(**locals())
            c.copy_expert(sql, out)
      
    def create_constraints(self):
        pass
