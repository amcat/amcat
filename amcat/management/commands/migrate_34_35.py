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

from django.core.management import BaseCommand
from django.db import connection
from django.db import models

from bulk_update.helper import bulk_update

from amcat.tools import amcates
from amcat.models import Article

NEW_FIELDS = {"hash": "bytea", "parent_hash": "bytea", "properties" : "jsonb", "title": "text"}
PROP_FIELDS = "section", "pagenr", "byline", "length", "metastring", "externalid", "author", "addressee", "uuid"

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
        # headline -> title
        cursor.execute('UPDATE articles SET title=headline')
        
        # other fields -> properties
        fields = ", ".join("'{field}', \"{field}\"".format(**locals()) for field in PROP_FIELDS)
        fields = "{fields}, 'medium', m.name".format(**locals())
        sql = '''UPDATE articles a SET properties = json_strip_nulls(json_build_object({fields}))
                 FROM media m WHERE m.medium_id = a.medium_id'''.format(**locals())
        cursor.execute(sql)
        
        # build hashes
        # ('hashable' fields should now all be updated, so can use django ORM)
        # parent_hash is part of hash, so need to do it in 'layers'
        models.IntegerField().contribute_to_class(Article, 'parent_article_id')

        max_id = Article.objects.aggregate(models.Max('pk'))['pk__max']
        batch_size = 1000
        n = (max_id // batch_size) + 1
        parents = {}
        for batch in range(0, n):
            to_update = []
            logging.info("\rHashing articles without parents, batch {i} / {n}".format(i=batch+1, **locals()))
            _from, _to = batch * batch_size, (batch+1)*batch_size
            articles = list(Article.objects.filter(pk__gt=_from, pk__lte=_to))
            for a in articles:
                if a.parent_article_id:
                    parents[a.id] = a.parent_article_id
                else:
                    a.hash = amcates.get_article_dict(a)['hash']
                    to_update.append(a)
            bulk_update(to_update, update_fields=['hash'])
        
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
        cursor.execute('ALTER TABLE articles CREATE INDEX ON parent_hash')
        

    def drop_columns(self):
        cursor = connection.cursor()
        for col in PROP_FIELDS + ('headline', 'medium_id', 'insertscript', 'insertdate', 'parent_article_id'):
            cursor.execute('ALTER TABLE articles DROP COLUMN IF EXISTS "{col}"'.format(**locals()))

