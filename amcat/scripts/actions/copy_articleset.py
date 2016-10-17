#!/usr/bin/python
# ##########################################################################
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
Script to import an articleset from another AmCAT instance using psql COPY

Currently hardwired to copy to amcatdb2
"""

import subprocess
import logging
import csv

from django import forms
from django.conf import settings

from django.db import transaction

from amcat.models import Project, ArticleSet, Article, Medium
from amcat.scripts.script import Script

from amcat.tools.toolkit import splitlist


try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

log = logging.getLogger(__name__)

ARTICLE_FIELDS = ["date", "section", "pagenr", "title", "byline", "length", "metastring", "url",
                  "externalid", "author", "text", "medium_id", "uuid"]


class CopyArticleSetScript(Script):
    class options_form(forms.Form):
        source_host = forms.CharField()
        source_db = forms.CharField(initial='amcat')
        source_set_id = forms.IntegerField()
        destination_project = forms.ModelChoiceField(queryset=Project.objects.all(), required=False)
        destination_set_id = forms.ModelChoiceField(queryset=ArticleSet.objects.all(), required=False)

    def run(self, _input=None):
        self.source_set_id, self.source_host, self.source_db, self.dest_project, self.dest_set = [
            self.options.get(x) for x in ("source_set_id", "source_host", "source_db",
                                          "destination_project", "destination_set_id")]
        self.source_port = 5432

        self.dest_host = settings.DATABASES['default']['HOST']
        self.dest_db = settings.DATABASES['default']['NAME']
        self.dest_port = settings.DATABASES['default']['PORT']

        if self.dest_host == self.source_host and self.dest_db == self.source_db and self.dest_port == self.source_port:
            raise Exception("Destination and source host are the same: {self.dest_host}:{self.dest_db}"
                            .format(**locals()))

        if self.dest_project is None:
            if self.dest_set is None:
                raise Exception("Please specify either destination project or articleset id")
            self.dest_project = self.dest_set.project

        log.info(
            "Moving articles from source {self.source_host!r}:{self.source_db}:{self.source_port} set {self.source_set_id} "
            "to destination {self.dest_host!r}:{self.dest_db!r}:{self.source_port} "
            .format(**locals()))

        self._assign_uuids()

        uuids, media = self._get_uuids()
        log.info("{n} articles in source set, UUIDs and media collected".format(n=len(uuids)))

        aids = list(self._check_uuids(uuids))
        log.info("{n} articles need to be copied to destionation".format(n=len(aids)))

        self._check_media(media)

        self._copy_articles(aids)


        # only needed if dest_set is None, but let's keep it out of the transaction as it involves a source db call
        name, provenance = self._get_index_details()

        with transaction.atomic:
            if self.dest_set is None:
                provenance = "Imported from {self.source_host} set {self.source_set_id}\n{provenance}".format(
                    **locals())
                log.info("Creating destination articleset {name!r} with provenance {provenance!r}".format(**locals()))
                self.dest_set = ArticleSet.objects.create(project=self.dest_project, name=name, provenance=provenance)
                log.info("Created destination articleset {self.dest_set.id}:{self.dest_set.name!r} "
                         "in project {self.dest_project.id}:{self.dest_project.name!r}"
                         .format(**locals()))

            self._add_to_set(uuids.keys())

    def _assign_uuids(self):
        log.info("Assigning uuids to articles in the source set as needed")
        sql = ("UPDATE articles SET uuid=uuid_generate_v1() "
               "WHERE uuid IS NULL AND article_id IN ( "
               "    SELECT article_id FROM articlesets_articles WHERE articleset_id={self.source_set_id}"
               ")".format(**locals()))
        result = self._execute_source_sql(sql)
        log.debug("SQL Result: {result}".format(**locals()))


    def _check_uuids(self, uuids):
        """Check which articles are already present in the destination database
        Returns a sequence of articles ids that are NOT present, ie that need to be copied"""
        for i, batch in enumerate(splitlist(uuids.keys(), itemsperbatch=10000)):
            log.info("({i}) Checking whether {n} uuids are present in destination database"
                     .format(n=len(batch), **locals()))

            present = {uuid for (uuid,) in Article.objects.filter(uuid__in=batch).values_list("uuid")}
            for uuid in set(batch) - present:
                yield uuids[uuid]


    def _execute_source_sql(self, sql):
        cmd = ["psql", "-h", self.source_host, self.source_db, "-c", sql]
        return subprocess.check_output(cmd)

    def _do_source_query(self, sql):
        # django db will be the dest database so a simple way to query to source db
        # I presume this is also possible with multiple databases, but no idea how to set that up
        # on the fly...
        sql = "COPY ({sql}) TO STDOUT WITH CSV".format(**locals())
        result = self._execute_source_sql(sql)
        return csv.reader(StringIO(result))


    def _get_uuids(self):
        sql = ("SELECT a.article_id, uuid, medium_id FROM articles a"
               " INNER JOIN articlesets_articles s ON a.article_id = s.article_id"
               " WHERE articleset_id = {self.source_set_id}".format(**locals()))
        uuids, media = {}, set()
        for aid, uuid, medium_id in self._do_source_query(sql):
            if not uuid.strip():
                raise Exception("Not all articles have UUIDs")
            uuids[uuid] = int(aid)
            media.add(int(medium_id))
        return uuids, media

    @transaction.atomic
    def _check_media(self, media):
        log.debug("Checking whether media {media!r} are present in the destination db".format(**locals()))
        source_media = {mid for (mid,) in Medium.objects.filter(pk__in=media).values_list('id')}
        missing = set(media) - source_media
        if missing:
            log.debug("Will create messing media {missing}".format(**locals()))
            sql = ("SELECT medium_id, name FROM media WHERE medium_id IN ({media})"
                   .format(media=",".join(map(str, missing))))
            for mid, name in self._do_source_query(sql):
                Medium.objects.create(id=mid, name=name)

    def _get_index_details(self):
        sql = ("SELECT name, provenance FROM articlesets"
               " WHERE articleset_id = {self.source_set_id}".format(**locals()))
        name, provenance = next(iter(self._do_source_query(sql)))
        return name, provenance

    def _copy_articles(self, aids):
        for batch in splitlist(aids, itemsperbatch=1000):
            self._do_copy_articles(batch)

    def _do_copy_articles(self, aids):
        # Create the article objects
        fields = ", ".join(ARTICLE_FIELDS)
        article_ids = ", ".join(map(str, aids))
        export_sql = ("SELECT {self.dest_project.id} AS projectid, {fields} FROM articles a"
                      " WHERE article_id IN ({article_ids})").format(**locals())
        export_sql = "COPY ({export_sql}) TO STDOUT WITH BINARY".format(**locals())

        import_sql = "COPY articles (project_id, {fields}) FROM STDIN WITH BINARY".format(**locals())

        dest_host = "-h {self.dest_host}".format(**locals()) if self.dest_host else ""
        dest_port = "-p {self.dest_port}".format(**locals()) if self.dest_port else ""
        source_host = "-h {self.source_host}".format(**locals()) if self.source_host else ""

        cmd = ('psql {source_host} {self.source_db} -c "{export_sql}" '
               '| psql {dest_port} {dest_host} {self.dest_db} -c "{import_sql}"').format(**locals())

        log.debug("Copying {n} articles...".format(n=len(aids)))
        #log.debug(cmd)
        subprocess.check_output(cmd, shell=True)
        log.debug("... Done!")

    def _add_to_set(self, uuids):
        log.debug("Adding {n} articles to set using uuids...".format(n=len(uuids)))
        aids = [aid for (aid,) in Article.objects.filter(uuid__in=uuids).values_list("id")]
        if len(aids) != len(uuids):
            raise Exception("|aids| != |uuids|, something went wrong importing...")
        self.dest_set.add_articles(aids, add_to_index=False)
        log.debug("... Done!")

