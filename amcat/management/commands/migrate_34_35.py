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

Before migrating, you need to dump the articles and media tables using something like:

psql -c "copy media to 'media.csv' with csv header" amcat
psql -c "copy articles to 'articles.csv' with csv header" amcat

And provide these csv files as arguments to migrate_34_35

The DB migration will do the following:
- drop and re-create the articles table
- copy the data from the csv file (in multiple passes to fix parents)
- add UNIQUE and FK contraints

As this *will* delete all data, please make sure that you have a backup before running this!

After this, you should probably tell django that the initial migration is done: 
python -m amcat.manage migrate --fake amcat 0001
python -m amcat.manage migrate --fake amcat 0002
Now, you can re-index the elasticsearch index
"""

import sys
import logging
import binascii
import csv
import io
import json
import itertools
from datetime import datetime
import ctypes

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

SKIP_PARENTS = 108501253, 86389974

class Command(BaseCommand):
    
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('articles', help="CSV file containing the articles dump")
        parser.add_argument('media', help="CSV file containing the media dump")
        parser.add_argument('--dry-run', action='store_true', help="Don't alter the database")
        parser.add_argument('--continue', action='store_true', help="Continue an aborted migration")
        parser.add_argument('--max-id', type=int, help="Manually set highest ID, should be at least the actual max_id")

        
    def handle(self, *args, **options):
        self.n_rows = "?"
        self.maxid = options['max_id']
        self.dry = options['dry_run']
        self._continue = options['continue']
        if not (self.dry or self._continue):
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
            if out.tell() > 100000000:
                self.do_copy(out, i)
                out = io.StringIO()
                outw = csv.writer(out, quoting=csv.QUOTE_ALL)

        if out.tell():
            self.do_copy(out, i)

    def do_copy(self, out, i):
        logging.info("[{}%] {} copying {} bytes, {i}/{self.n_rows} articles"
                     .format((i*100)//self.n_rows, "NOT " if self.dry else "", out.tell(),**locals()))        
        if self.dry:
            return
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


        r = csv.reader(open(fn))
        header = next(r)
        index = {col: i for (i, col) in enumerate(header)}
        AID = index['article_id']
        if self.maxid:
            logging.info("*** max(id) set by user: {self.maxid}".format(**locals()))
            max_id, self.n_rows = self.maxid, self.maxid
        else:
            logging.info("*** Scan input CSV to determine #rows and max(id)")
            for row in r:
                max_id = max(max_id, int(row[AID]))
                self.n_rows += 1
                if not self.n_rows  % 10000000:
                    logging.info(".. scanned {self.n_rows} rows".format(**locals()))
                    
        logging.info("{self.n_rows} rows, max ID {max_id}, allocating memory for hashes".format(**locals()))

        hashes = ctypes.create_string_buffer(max_id*28)
        NULL_HASH = b'\x00' * 28
        orphans = "N/A"
        passno = 1

        if self._continue:
            logging.info("Continuing from previous migration, getting state from DB")
            with connection.cursor() as c:
                c.execute("SELECT article_id, hash FROM articles")
                while True:
                    rows = c.fetchmany(10000)
                    if not rows:
                        break
                    self.n_rows -= len(rows)
                    for (aid, hash) in rows:
                        offset = (aid - 1) * 28
                        hashes[offset:offset+28] = hash
            logging.info("Continuing migration, {self.n_rows} articles to go".format(**locals()))
        
        while orphans:
            logging.info("*** Pass {passno}, #orphans {orphans}".format(**locals()))
            passno += 1
            orphans = 0
            
            r = csv.reader(open(fn))
            next(r) # skip header

            for row in r:
                aid = int(row[AID])
                
                offset = (aid - 1) * 28
                stored_hash = hashes[offset:offset+28]
                if stored_hash != NULL_HASH:
                    continue
                
                parent_id = _int(row[index['parent_article_id']])
                if (parent_id == aid) or (parent_id in SKIP_PARENTS):
                    parent_id = None
                if parent_id:
                    poffset = (parent_id - 1) * 28
                    parent_hash = hashes[poffset:poffset+28]
                    if parent_hash == NULL_HASH:
                        orphans += 1
                        continue
                    parent_hash = binascii.hexlify(parent_hash).decode("ascii")
                else:
                    parent_hash = None

                date = row[index['date']]
                date = date.split("+")[0]
                date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')

                
                a = Article(
                    project_id = row[index['project_id']],
                    date = date,
                    title = row[index['headline']],
                    url = row[index['url']] or None,
                    text = row[index['text']],
                    parent_hash=parent_hash)
                
                a.properties = {v: row[index[v]] for v in PROP_FIELDS if row[index[v]]}
                a.properties['medium'] = media[int(row[index['medium_id']])]
                a.properties['uuid'] = str(a.properties['uuid'])
                props = json.dumps(a.properties)
            
                hash = amcates.get_article_dict(a)['hash']
                hashes[offset:offset+28] = binascii.unhexlify(hash)

                yield (a.project_id, aid, a.date, a.title, a.url, a.text,
                       hash2binary(hash), hash2binary(a.parent_hash), props)
            
    def create_constraints(self):
        pass
