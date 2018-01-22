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
import tempfile
import shutil
import zipfile


from django import forms
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder

from amcat.scripts.script import Script
from amcat.models import *
from amcat.models.user import User
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

        if output.endswith(".zip"):
            self.folder = tempfile.mkdtemp()
            logging.debug("Writing output to temporary folder {self.folder}".format(**locals()))
        else:
            os.mkdir(output) 
            self.folder = output
        
        logging.info("Exporting project {project.id}:{project} to {output}".format(**locals()))

        try:
            self.codebook_fields = set()  # which fields do we need to serialize to uuid?
            self.codes = {}  # code_id -> uuid
            
            self.project = project
            
            self.schema_ids = self.get_schema_ids()
            self.codebook_ids = self.get_codebook_ids()

            self.export_users()
            self.export_articlesets()

            self.export_articles()
            self.export_articlesets_articles()

            
            self.codebook_ids = self.export_codebooks()
            self.export_codingschemas()
            self.export_codingjobs()
            
            if output.endswith(".zip"):
                logging.info("Creating zipfile {output}".format(**locals()))
                with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, allowZip64 = True) as z:
                    for f in os.listdir(self.folder):
                        z.write(os.path.join(self.folder, f), f)
        finally:
            if output.endswith(".zip"):
                shutil.rmtree(self.folder)
        logging.info("Done")

    def _get_codingjob_values(self, ca_ids, batch_size=1000):
        def serialize_coding_value(cv):
            result = dict(codingschemafield_id=cv.field_id, intval=cv.intval, strval=cv.strval)
            if cv.field_id in self.codebook_fields:
                intval = result['intval']
                try:
                    result["code"] = self.codes[intval]
                    del result['intval']
                except KeyError:
                    ca = cv.coding.coded_article
                    logging.warn("Could not find code {intval} in job {ca.codingjob_id} article {ca.article_id} , was it removed from the codebook?".format(**locals()))
                    pass
            return result
        
        def get_values_dict(coding):
            s = coding.sentence
            return dict(sentence=(s and [s.parnr, s.sentnr] or None),
                        start=coding.start, end=coding.end,
                        values=[serialize_coding_value(cv) for cv in coding.values.all()])
                    
        for i, batch in enumerate(toolkit.splitlist(ca_ids, itemsperbatch=batch_size)):
            logging.info("... batch {i}/{n}".format(n=len(ca_ids)//batch_size, **locals()))
            codings_per_article = collections.defaultdict(list)
            for c in Coding.objects.filter(coded_article_id__in=batch).prefetch_related("values").select_related("sentence"):
                codings_per_article[c.coded_article_id].append(c)
            for caid, codings in codings_per_article.items():
                yield dict(coded_article_id=caid, codings=[get_values_dict(c) for c in codings])
                
    def get_sentences(self, aids, batch_size=1000):
        for i, batch in enumerate(toolkit.splitlist(aids, itemsperbatch=batch_size)):
            logging.info("... batch {i}/{n}".format(n=len(aids)//batch_size, **locals()))
            articles = {}
            for aid, parnr, sentnr, sentence in (Sentence.objects.filter(article_id__in=batch).distinct()
                                                 .values_list("article_id", "parnr", "sentnr", "sentence")):
                articles.setdefault(aid, []).append((parnr, sentnr, sentence))
            for aid, sentences in articles.iteritems():
                yield dict(article_id=aid, sentences=sentences)
        

    def export_codingjobs(self):
        cjs = json.loads(serializers.serialize("json", CodingJob.objects.filter(project=self.project)))
        coders = dict(User.objects.filter(pk__in={cj["fields"]["coder"] for cj in cjs}).values_list("pk", "email"))
        def substitute_email(coder, **fields):
            return dict(coder=coders[coder], **fields)
        cjs = [substitute_email(pk=c["pk"], **c["fields"]) for c in cjs]
        self._write_json_lines("codingjobs", cjs)
        
        #self._serialize("codingjobs", CodingJob.objects.filter(project=self.project))
        cas = CodedArticle.objects.filter(codingjob__project=self.project)
        coded_articles = self._serialize("codedarticles", cas)
        ca_ids = [ca.id for ca in coded_articles]
        self._write_json_lines("codingvalues", self._get_codingjob_values(ca_ids))

        #serialize sentences
        sentences = self.get_sentences({ca.article_id for ca in coded_articles})
        self._write_json_lines("sentences", sentences, "coded sentences")
        
    def export_users(self):
        roles = {r.user_id: r.role.label for r in self.project.projectrole_set.all()}
        cjs = CodingJob.objects.filter(project=self.project)
        uids = set(roles) | {self.project.insert_user.pk} | {cj.coder_id for cj in cjs}
        def get_users(uids, roles):
            for u in User.objects.filter(pk__in=uids):
                role = roles.get(u.id)
                yield dict(username=u.username, first_name=u.first_name, last_name=u.last_name, password=u.password, role=role, email=u.email)
        self._write_json_lines("users", get_users(uids, roles))


    def get_schema_ids(self):
        # we need to serialize coding schemas that are either part of this project, linked in this project, or using in a codingjob
        # TODO: require read access on the other projects?
        ids = set(CodingSchema.objects.filter(project=self.project).values_list("pk", flat=True))
        ids |= set(self.project.codingschemas.values_list("pk", flat=True))
        for schemas in CodingJob.objects.filter(project=self.project).values_list("articleschema_id", "unitschema_id"):
            ids |= set(schemas)
        return ids

    def get_codebook_ids(self):
        # serialize codebooks that are either part of this project, *or* used in a coding schema in this project
        # TODO: require read access on the other projects?
        ids = set(Codebook.objects.filter(project=self.project).values_list("pk", flat=True))
        ids |= set(self.project.codebooks.values_list("pk", flat=True))
        ids |= set(CodingSchemaField.objects.filter(codingschema_id__in=self.schema_ids, codebook__isnull=False).values_list("codebook_id", flat=True))
        return ids
        
    def export_codingschemas(self):
        self._serialize("codingschemas", CodingSchema.objects.filter(pk__in=self.schema_ids))
        for f in self._serialize("codingschemafields", CodingSchemaField.objects.filter(codingschema_id__in=self.schema_ids)):
            if f.fieldtype_id == FIELDTYPE_IDS.CODEBOOK:
                self.codebook_fields.add(f.id)
        
    def export_codebooks(self):
        ids = self.codebook_ids
        for c in self._serialize("codes", Code.objects.filter(codebook_codes__codebook__in=ids).distinct()):
            self.codes[c.pk] = unicode(c.uuid)
        self._serialize("labels", Label.objects.filter(code__codebook_codes__codebook__in=ids)
                        .select_related("code__uuid").select_related("language__label").distinct())
        self._serialize("codebooks", Codebook.objects.filter(pk__in=ids).distinct())
        self._serialize("codebookcodes", CodebookCode.objects.filter(codebook__in=ids).distinct())

    def export_articlesets(self):
        self.sets = set(self.project.articlesets_set.all())
        self.sets |= {cj.articleset for cj in CodingJob.objects.filter(project=self.project)}
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
        ids = set(ES().query_ids(filters=dict(sets=[s.id for s in self.sets])))
        # make sure all codingjob articles are in here, even if the set was modified after coding
        ids |= set(CodedArticle.objects.filter(codingjob__project=self.project).values_list("article_id", flat=True))
        with self._output_file("articles", extension="jsonl") as f1:
            with self._output_file("articles_with_parents", extension="jsonl") as f2:
                logging.info("Writing articles to {f1.name} and {f2.name}".format(**locals()))
                for d in self._generate_all_articles(ids):
                    f = f2 if d.get('parent_id') else f1
                    json.dump(d, f, cls=DjangoJSONEncoder)
                    f.write("\n")


    def _generate_article(self, a, medium):
        props = {prop: getattr(a, prop) for prop in PROP_FIELDS if getattr(a, prop)}
        if 'uuid' in props:
            props['uuid'] = unicode(props['uuid'])
        props['medium'] = medium
            
        d = dict(date = a.date,
                 title = a.headline,
                 url = a.url,
                 text = a.text,
                 properties = props,
                 old_id = a.id)
        if a.parent_id:
            d['parent_id'] = a.parent_id
        return d
        
    def _generate_all_articles(self, ids):
        media = {}
        for batch in splitlist(ids, itemsperbatch=10):
            articles = list(Article.objects.filter(pk__in=batch))
            unknown_media = {a.medium_id for a in articles} - set(media)
            if unknown_media:
                media.update({m.id : m.name for m in Medium.objects.filter(pk__in=unknown_media)})
            for a in articles:
                yield self._generate_article(a, media[a.medium_id])
            
        
    @contextmanager
    def _output_file(self, fn, extension="json"):
        fn = os.path.join(self.folder, ".".join([fn, extension]))
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
            return []
        with self._output_file(fn, extension="json") as f:
            logging.info("Writing {} {logmessage} to {f.name}".format(len(queryset), **locals()))
            ser = serializers.get_serializer("json")()
            objects = list(queryset)
            ser.serialize(queryset, stream=f, use_natural_primary_keys=True, use_natural_foreign_keys=True)
            return objects


@contextmanager        
def _print_queries(msg=None):
    from django.db import connection, reset_queries
    import time
    t = time.time()
    reset_queries()
    try:
        print("------------------- START {} --------------".format(msg or ""))
        yield
    finally:
        for q in connection.queries:
            print("- {time} - {sql}".format(**q))
        print("------------------- {:.3f}s END {} --------------".format(time.time() - t, msg or ""))
        
if __name__ == '__main__':
    import django
    django.setup()
    
    from amcat.scripts.tools import cli
    result = cli.run_cli()

