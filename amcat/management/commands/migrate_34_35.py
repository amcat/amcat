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
import itertools
from datetime import datetime

import psycopg2

from django.core.management import BaseCommand
from django.db import connection
from django.db import models

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
        parser.add_argument('--dry-run', action='store_true', help="Don't alter the database")
        
    def handle(self, *args, **options):
        self.dry = options['dry_run']
        if not self.dry:
            self.drop_old()
            self.create_article_table()
        media = dict(self.get_media(options['media']))
        logging.info("Read {} media".format(len(media)))
        self.copy_data(options['articles'], media)
        if not self.dry:
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
        cursor = connection.cursor()
        
        out = io.StringIO()
        outw = csv.writer(out, quoting=csv.QUOTE_ALL)
        for i, row in enumerate(self.get_articles(fn, media)):
            outw.writerow(row)
            if out.tell() > 10000000:
                self.do_copy(out, i)
                out = io.StringIO()
                outw = csv.writer(out, quoting=csv.QUOTE_ALL)

        if out.tell():
            self.do_copy(out, i)

    def do_copy(self, out, i):
        if self.dry:
            logging.info("(NOT) Copying {} bytes to postgres, total {} articles".format(out.tell(), i))
            return
        logging.info("Copying {} bytes to postgres, total {} articles".format(out.tell(), i))
        out.seek(0)
        with connection.cursor() as c:
            cols = ", ".join(['project_id', 'article_id', 'date', 'title', 'url', 'text', 'hash', 'parent_hash', 'properties'])
            sql = "COPY articles ({cols}) FROM STDIN WITH (FORMAT CSV, FORCE_NULL (url, parent_hash))".format(**locals())
            c.copy_expert(sql, out)
            
    def get_articles(self, fn,  media):
        csv.field_size_limit(sys.maxsize)
        def _int(x):
            return int(x) if x else None
        def hash2binary(hash):
            if hash:
                if not isinstance(hash, str):
                    raise TypeError("Hash should be str, not {}".format(type(hash)))
                return "\\x" + hash
        
        hashes = {} # id : hash_bytes (bytes to save memory, this will store *all* articles!)
        orphans = "N/A"
        
        while orphans:
            logging.info("*** Next pass, stored {n}, orphans {orphans}".format(n=len(hashes), **locals()))

            orphans = 0
            r = csv.reader(open(fn))
            header = next(r)
            index = {col: i for (i, col) in enumerate(header)}

            for row in r:
                aid = int(row[index['article_id']])
                if aid in hashes:
                    continue
                
                parent_id = _int(row[index['parent_article_id']])
                if parent_id and parent_id not in hashes:
                    orphans += 1
                    continue

                date = row[index['date']]
                date = date.split("+")[0]
                date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')

                
                a = Article(
                    project_id = row[index['project_id']],
                    date = date,
                    title = row[index['headline']],
                    url = row[index['url']] or None,
                    text = row[index['text']])
                
                a.properties = {v: row[index[v]] for v in PROP_FIELDS if row[index[v]]}
                a.properties['medium'] = media[int(row[index['medium_id']])]
                a.properties['uuid'] = str(a.properties['uuid'])
                props = json.dumps(a.properties)
                
                if parent_id:
                    a.parent_hash = binascii.hexlify(hashes[parent_id]).decode("ascii")
            
                hash = amcates.get_article_dict(a)['hash']
                hashes[aid] = binascii.unhexlify(hash)

                yield (a.project_id, aid, a.date, a.title, a.url, a.text,
                       hash2binary(hash), hash2binary(a.parent_hash), props)
            
    def create_constraints(self):
        pass
