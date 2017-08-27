import json
from zipfile import ZipFile
import logging

from django import forms
import django
from django.core import serializers

django.setup()

from amcat.models import Article, ArticleSet, Project, Code, Label, CodebookCode, CodedArticle
from amcat.tools import toolkit, sbd
from amcat.scripts.script import Script


class ImportProject(Script):
    class options_form(forms.Form):
        file = forms.FileField()
        project = forms.ModelChoiceField(queryset=Project.objects.all(), required=False)

    def _run(self, file, project):
        from amcat.models import Project
        self.setids = {}  # old_id -> new_id
        self.articles = {}  # old_id -> new_id
        self.schemafields = {}  # old_id -> new_id
        self.codes = {}  # uuid -> id

        self.zipfile = ZipFile(file.file.name)
        self.project = project if project else Project.objects.create(name=file.file.name, owner_id=1)
        logging.info("Importing {file.file.name} into project {self.project.id}:{self.project.name}"
                     .format(**locals()))
        self.import_articlesets()
        self.import_articles()
        self.import_articlesets_articles()
        self.import_codes()

        self.codebooks = self.import_codebooks()
        self.import_codebookcodes()
        self.import_codingschemas()
        self.codingjobs = dict(self.import_codingjobs())

        self.import_codings()

        logging.info("Done!")

    def _save_with_id_mapping(self, objects):
        for o in objects:
            old_id = o.object.pk
            o.object.pk = None
            if hasattr(o.object, "project_id"):
                o.object.project_id = self.project.id
            o.save()
            yield old_id, o.object.pk

    def import_codingjobs(self):
        jobs = self._deserialize("codingjobs.json")
        for job in jobs:
            if job.object.articleschema_id:
                job.object.articleschema_id = self.codingschemas[job.object.articleschema_id]
            if job.object.unitschema_id:
                job.object.unitschema_id = self.codingschemas[job.object.unitschema_id]
            job.object.articleset_id = self.setids[job.object.articleset_id]

        return self._save_with_id_mapping(jobs)

    def import_codings(self):
        db_cas = {(ca.codingjob_id, ca.article_id): ca
                  for ca in CodedArticle.objects.filter(codingjob__project=self.project)}
        cas = self._deserialize("codedarticles.json")
        codedarticles = {}
        for ca in cas:
            db_ca = db_cas[self.codingjobs[ca.object.codingjob_id], self.articles[ca.object.article_id]]
            db_ca.comments = ca.object.comments
            db_ca.status_id = ca.object.status_id
            db_ca.save()
            codedarticles[ca.object.pk] = db_ca
        for a in self._get_dicts("codingvalues.jsonl"):
            ca = codedarticles[a["coded_article_id"]]
            sdict = {(s.parnr, s.sentnr): s.pk for s in sbd.get_or_create_sentences(ca.article)}
            print(sdict)

            for c in a["codings"]:
                print(c)
                s = c.pop("sentence")
                c["sentence_id"] = None if s is None else sdict[tuple(s)]
                for v in c["values"]:
                    v["codingschemafield_id"] = self.schemafields[v["codingschemafield_id"]]
                    if "code" in v:
                        v["intval"] = self.codes[v.pop("code")]
            ca.replace_codings(a["codings"])


    def import_codingschemas(self):
        self.codingschemas = dict(self._save_with_id_mapping(self._deserialize("codingschemas.json")))
        for f in self._deserialize("codingschemafields.json"):
            old_id = f.object.pk
            f.object.pk = None
            f.object.codingschema_id = self.codingschemas[f.object.codingschema_id]
            if f.object.codebook_id:
                f.object.codebook_id = self.codebooks[f.object.codebook_id]
            f.save()
            self.schemafields[old_id] = f.object.pk

    def import_codes(self):
        for c in self._deserialize("codes.json"):
            if not c.object.pk:
                c.save()
            self.codes[c.object.uuid] = c.object.pk
        Label.objects.bulk_create(c.object for c in self._deserialize("labels.json") if not c.object.pk)

    def import_codebooks(self):
        return dict(self._save_with_id_mapping(self._deserialize("codebooks.json")))

    def import_codebookcodes(self):
        cbcodes = [c.object for c in self._deserialize("codebookcodes.json")]
        for c in cbcodes:
            c.codebook_id = self.codebooks[c.codebook_id]
            c.pk = None
        CodebookCode.objects.bulk_create(cbcodes)

    def import_articlesets(self):
        for a in self._get_dicts("articlesets.jsonl"):
            aset = ArticleSet.objects.create(project=self.project, name=a['name'], provenance=a['provenance'])
            self.setids[a['old_id']] = aset.id
            if a['favourite']:
                self.project.favourite_articlesets.add(aset)

    def import_articles(self):
        for i, batch in enumerate(toolkit.splitlist(self._get_dicts("articles.jsonl"), itemsperbatch=1000)):
            logging.info("Import articles batch {i}".format(**locals()))
            uuids = {a['properties']['uuid'] : a.pop('old_id') for a in batch}
            articles = Article.create_articles([Article(project_id=self.project.id, **a) for a in batch])
            self.articles.update({uuids[a.get_property('uuid')]: a.id for a in articles})

    def import_articlesets_articles(self):
        for a in self._get_dicts("articlesets_articles.jsonl"):
            aids = [self.articles[aid] for aid in a['articles']]
            setid = self.setids[a['articleset']]
            ArticleSet.objects.get(pk=setid).add_articles(aids)

    def _get_dicts(self, fn):
        if fn not in self.zipfile.namelist():
            logging.info("No {fn}".format(**locals()))
        else:
            logging.info("Reading {fn}".format(**locals()))
            for line in self.zipfile.open(fn):
                yield json.loads(line.decode("utf-8"))

    def _deserialize(self, fn):
        if fn not in self.zipfile.namelist():
            logging.info("No {fn}".format(**locals()))
            return []
        else:
            result = list(serializers.deserialize("json", self.zipfile.open(fn)))
            logging.info("Read {} entries from {fn}".format(len(result), **locals()))
            return result


if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()