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
        parser.add_argument('--no_data', action='store_true', help="Don't copy the date to property fields")
        parser.add_argument('--drop_columns', action='store_true', help="Drop the unneeded columns after migrating")
        
    def handle(self, *args, **options):
        self.create_fields()
        if not options['no_data']:
            self.copy_data()
        if options['drop_columns']:
            self.drop_columns()

    def create_fields(self):
        to_add = NEW_FIELDS.copy()
        cursor = connection.cursor()
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' and table_name = 'articles'")
        for column_name, data_type in cursor.fetchall():
            if column_name in to_add:
                target_type = to_add.pop(column_name)
                if target_type != data_type:
                    raise ValueError("Error in column {column_name}: existing type {data_type} != target type {target_type}".format(**locals()))

        if not to_add:
            logging.info("All DB columns already exist")
        else:
            logging.info("Creating columns: {to_add!r}".format(**locals()))
            for col, typ in to_add.items():
                sql = 'ALTER TABLE "articles" ADD COLUMN "{col}" {typ}'.format(**locals())
                cursor.execute(sql)
        
    def copy_data(self):
        cursor = connection.cursor()
        # Add 'old' fields to model so we can easily retrieve them:
        models.IntegerField().contribute_to_class(Article, 'parent_article_id')
        models.IntegerField().contribute_to_class(Article, 'medium_id')
        models.TextField().contribute_to_class(Article, 'headline')
        for (name, ftype) in PROP_FIELDS.items():
            ftype().contribute_to_class(Article, name)

        logging.info("Getting medium names")
        cursor.execute("SELECT medium_id, name FROM media")
        media = dict(cursor.fetchall())
            
        # convert articles and build hashes
        # parent_hash is part of hash, so need to do it in 'layers'
        # Do it in batches to prevent memory (and postgres) blowing up
        max_id = Article.objects.aggregate(models.Max('pk'))['pk__max']
        batch_size = 1000
        n = (max_id // batch_size) + 1
        parents = {} # for articles whose parent hash is not yet known
        hashes = {} # article : hash_bytes
        for batch in range(0, n):
            logging.info("Updating articles, first pass, batch {i} / {n}".format(i=batch+1, **locals()))
            _from, _to = batch * batch_size, (batch+1)*batch_size
            articles = list(Article.objects.filter(pk__gt=_from, pk__lte=_to))
            for a in articles:
                a.title = a.headline
                a.properties = {v: getattr(a, v) for v in PROP_FIELDS if getattr(a,v)}
                a.properties['medium'] = media[a.medium_id]
                a.properties['uuid'] = str(a.properties['uuid'])

                parent = a.parent_article_id
                if parent and (parent not in hashes):
                    # defer to next pass
                    parents[a.id] = a.parent_article_id
                else:
                    if parent: 
                        a.parent_hash = binascii.hexlify(hashes[parent])
                    a.hash = amcates.get_article_dict(a)['hash']
                    hashes[a.id] = binascii.unhexlify(a.hash)
                    
            bulk_update(articles, update_fields=['title', 'properties', 'hash', 'parent_hash'])
        del hashes
        
        while parents:
            logging.info("Setting parent hash and computing child hashes, todo={}".format(len(parents)))
            batch = {aid: parent for (aid, parent) in parents.items() if parent not in parents}
            articles = Article.objects.only("pk").in_bulk(batch.keys())
            parent_hashes = dict(Article.objects.filter(pk__in=batch.values()).values_list("pk", "hash"))
            for aid, parent in batch.items():
                a = articles[aid]
                a.parent_hash = parent_hashes[parent]
                a.hash = amcates.get_article_dict(a)['hash']
                del parents[aid]
            bulk_update(list(articles.values()), update_fields=['hash', 'parent_hash'])

    
        cursor.execute('ALTER TABLE articles ALTER COLUMN title SET NOT NULL')
        cursor.execute('ALTER TABLE articles ALTER COLUMN text SET NOT NULL')
        cursor.execute('ALTER TABLE articles ALTER COLUMN hash SET NOT NULL')
        cursor.execute('ALTER TABLE articles ADD UNIQUE (hash)')
        cursor.execute('CREATE INDEX ON articles (parent_hash)')
        

    def drop_columns(self):
        cursor = connection.cursor()
        for col in PROP_FIELDS + ('headline', 'medium_id', 'insertscript', 'insertdate', 'parent_article_id'):
            cursor.execute('ALTER TABLE articles DROP COLUMN IF EXISTS "{col}"'.format(**locals()))

