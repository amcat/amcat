#!/usr/bin/python
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

from __future__ import unicode_literals

import logging
import os
import sys
from contextlib import contextmanager
from hashlib import sha224 as hash_class
import datetime
import re
import json
from binascii import hexlify, unhexlify

from django import forms
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder

from amcat.scripts.script import Script
from amcat.models import Project, Article, ArticleSetArticle, Medium, CodebookCode, Code, Label, Codebook
from amcat.tools.amcates import ES
from amcat.tools.toolkit import splitlist

log = logging.getLogger(__name__)

# amcat3.4 fields that are translated into 3.5 properties
PROP_FIELDS = ["section","pagenr", "byline", "length", "metastring", "externalid", "author", "addressee", "uuid"]


# Functions copied from amcat3.5 amcates (str -> unicode)
ARTICLE_FIELDS = ["text", "title", "url", "date", "parent_hash"]
_clean_re = re.compile('[\x00-\x08\x0B\x0C\x0E-\x1F]')

def _clean(s):
    """Remove non-printable characters and convert dates"""
    if not isinstance(s, (datetime.date, float, int, unicode, set, type(None))):
        raise ValueError("Cannot convert {} to elastic field: {}".format(type(s), s))

    if isinstance(s, set):
        return list(map(_clean, s))
    elif isinstance(s, unicode):
        # Convert non-printable characters to spaces
        return _clean_re.sub(' ', s)
    elif isinstance(s, datetime.datetime):
        return s.isoformat()
    elif isinstance(s, datetime.date):
        return datetime.datetime(s.year, s.month, s.day).isoformat()
    else:
        return s


def _escape_bytes(b):
    return b.replace(b"\\", b"\\\\").replace(b",", b"\\,")


def _hash_dict(d):
    c = hash_class()
    for fn in sorted(d.keys()):
        c.update(_escape_bytes(_encode_field(fn)))
        c.update(_escape_bytes(_encode_field(d[fn])))
        c.update(b",")
    return c.hexdigest()

def _encode_field(object, encoding="utf-8"):
    if isinstance(object, datetime.datetime):
        return object.isoformat().encode(encoding)
    elif isinstance(object, datetime.date):
        return datetime.datetime(object.year, object.month, object.day).isoformat().encode(encoding)
    return unicode(object).encode(encoding)

# based on amcat3.5 amcates get_article_dict
def get_amcat35_hash(adict):
    d = {field_name: _clean(adict[field_name]) for field_name in ARTICLE_FIELDS}
    for prop, val in adict['properties'].items(): 
        d[prop] = _clean(val)
    return _hash_dict(d)
    

class ExportProject(Script):
    """
    Export a project to a (zipped) collection of json files.
    """

    class options_form(forms.Form):
        project = forms.ModelChoiceField(queryset=Project.objects.all())
        output = forms.CharField(help_text="Output folder or zip file name")
        
    def _run(self, project, output):
        if os.path.exists(output):
            logging.error("Output {output} already exists!")
            sys.exit(1)

        os.mkdir(output)
        logging.info("Exporting project {project.id}:{project} to {output}".format(**locals()))

        self.project = project
        
        self.export_articlesets()
        self.export_articles()
        self.export_articlesets_articles()

        self.export_codebooks()

        logging.info("Done")

    @contextmanager
    def _output_file(self, fn, extension="json"):
        fn = os.path.join(self.options['output'], ".".join([fn, extension]))
        with open(fn, "w") as f:
            yield f

    def _write_json_lines(self, fn, dicts, logmessage=None):
        if logmessage is None:
            logmessage = fn
        with self._output_file(fn, extension="jsonl") as f:
            logging.info("Writing {logmessage} to {f.name}".format(**locals()))
            for d in dicts:
                json.dump(d, f, cls=DjangoJSONEncoder)
                f.write("\n")

    def _serialize(self, fn, queryset, logmessage=None):
        if logmessage is None:
            logmessage = fn
        if not queryset.exists():
            logging.info("No {logmessage} objects to serialize".format(**locals()))
        with self._output_file(fn, extension="json") as f:
            logging.info("Writing {} {logmessage} to {f.name}".format(len(queryset), **locals()))
            ser = serializers.get_serializer("json")()
            ser.serialize(queryset, stream=f, use_natural_primary_keys=True, use_natural_foreign_keys=True)

                
    def export_codebooks(self):
        from django.db import connection, reset_queries
        self._serialize("codes", Code.objects.filter(codebook_codes__codebook__project=self.project).distinct())
        self._serialize("labels", Label.objects.filter(code__codebook_codes__codebook__project=self.project)
                        .select_related("code__uuid").select_related("language__label").distinct())

        self._serialize("codebooks", Codebook.objects.filter(project=self.project).distinct())

        self._serialize("codebookcodes", CodebookCode.objects.filter(codebook__project=self.project).distinct())
        
    def export_articlesets(self):
        self.sets = list(self.project.articlesets_set.all())
        favs = set(self.project.favourite_articlesets.values_list("pk", flat=True))
        dicts = (dict(old_id=aset.id, provenance=aset.provenance, name=aset.name, favourite=aset.pk in favs)
                 for aset in self.sets)        
        self._write_json_lines("articlesets", dicts, "{} sets".format(len(self.sets)))

    def export_articlesets_articles(self):
        memberships = ES().query_field(filters=dict(sets=[s.id for s in self.sets]), field="sets")
        dicts = {s.id: {"articleset": s.id, "articles": []} for s in self.sets}
        for aid, sets in memberships:
            for aset in sets:
                if aset in dicts:
                    dicts[aset]["articles"].append(aid)
        self._write_json_lines("articlesets_articles", dicts.values())

    def export_articles(self):
        ids = list(ES().query_ids(filters=dict(sets=[s.id for s in self.sets])))
        self._write_json_lines("articles", self._generate_all_articles(ids))

        
    def _generate_article(self, a, medium):
        if a.parent:
            raise Exception("Project export does not support parents (yet)!")
        
        props = {prop: getattr(a, prop) for prop in PROP_FIELDS if getattr(a, prop)}
        if 'uuid' in props:
            props['uuid'] = unicode(props['uuid'])
        props['medium'] = medium
            
        return dict(date = a.date,
                 title = a.headline,
                 url = a.url,
                 text = a.text,
                 parent_hash = None,
                 properties = props,
                 old_id = a.id)
        
    def _generate_all_articles(self, ids):
        media = {}
        for batch in splitlist(ids, itemsperbatch=10):
            articles = list(Article.objects.filter(pk__in=batch))
            unknown_media = {a.medium_id for a in articles} - set(media)
            if unknown_media:
                media.update({m.id : m.name for m in Medium.objects.filter(pk__in=unknown_media)})
            for a in articles:
                yield self._generate_article(a, media[a.medium_id])
            
        
if __name__ == '__main__':
    import django
    django.setup()
    
    from amcat.scripts.tools import cli
    result = cli.run_cli()

