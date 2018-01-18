import json
import os
import tempfile
from itertools import count
from zipfile import ZipFile
import logging

from django import forms
import django
from django.core import serializers


from amcat.scripts.tools import cli
from amcat.models import Article, ArticleSet, Project, Label, CodebookCode, CodedArticle, User, CodingJob, Sentence
from amcat.tools import toolkit, sbd
from amcat.scripts.script import Script
from amcat.tools.djangotoolkit import bulk_insert_returning_ids


class ImportProject(Script):
    class options_form(forms.Form):
        file = forms.FileField()
        project = forms.ModelChoiceField(queryset=Project.objects.all(), required=False)
        user = forms.ModelChoiceField(queryset=User.objects.all())
        status_file = forms.CharField(required=False)

    def _run(self, file, project, user, status_file=None):
        from amcat.models import Project

        self.setids = {}  # old_id -> new_id
        self.articles = {}  # old_id -> new_id
        self.codes = {}  # uuid -> id
        self.codebooks = {} # old_id -> new_id
        self.codingschemas = {} # old_id -> new_id
        self.schemafields = {}  # old_id -> new_id
        self.codingjobs = {}
        self.sentences = False
        self.articlesets_articles = False
        self.user_id = user.id
        self.zipfile = ZipFile(file.file.name)
        self.coders = self.check_coders()  # email -> id

        #TODO replace self.x by status dict entries
        #TODO make sure calling import again doesn't duplicate things
        #TODO indexing
        if status_file:
            status = json.load(open(status_file))
            def _intkeys(key):
                return {int(k): v for (k, v) in status[key].items()} if key in status else {}

            self.project = Project.objects.get(pk=status['project'])
            self.setids = _intkeys('setids')
            self.articles = _intkeys('articles')
            self.codes = status.get('codes', {})
            self.codebooks = _intkeys('codebooks')
            self.codingschemas = _intkeys('codingschemas')
            self.schemafields = _intkeys('schemafields')
            self.codingjobs = _intkeys('codingjobs')
            self.sentences = status.get('sentences', False)
            self.articlesets_articles = status.get('articlesets_articles', False)

        else:
            status = {}
            self.project = project if project else Project.objects.create(name=file.file.name, owner_id=1)

        _, self.status_file = tempfile.mkstemp(suffix=".json", prefix="import_status_{}_".format(os.path.basename(file.file.name)))
        logging.info("Importing {file.file.name} into project {self.project.id}:{self.project.name}; status file: {self.status_file}"
                     .format(**locals()))

        if not self.setids:
            self.setids = dict(self.import_articlesets())
            self.save_status()
        if not self.articles:
            self.import_articles()
            self.save_status()

        if not self.articlesets_articles:
            self.import_articlesets_articles()
            self.articlesets_articles = True
            self.save_status()
        if not self.codes:
            self.codes = dict(self.import_codes())
            self.save_status()

        if not self.codebooks:
            self.codebooks = self.import_codebooks()
            self.import_codebookcodes()
            self.save_status()
        if not self.codingschemas:
            self.codingschemas, self.schemafields = self.import_codingschemas()
            self.save_status()
        if not self.codingjobs:
            self.codingjobs = dict(self.import_codingjobs())
            self.save_status()
        if not self.sentences:
            self.import_sentences()
            self.sentences = True
            self.save_status()
        self.import_codings()

        logging.info("Done!")

    def save_status(self):
        status = dict(setids=self.setids, articles=self.articles, project=self.project.id, codebooks=self.codebooks,
                      codes=self.codes, codingschemas=self.codingschemas, schemafields=self.schemafields,
                      codingjobs=self.codingjobs, articlesets_articles=self.articlesets_articles,
                      sentences=self.sentences)
        json.dump(status, open(self.status_file, "w"))
        logging.info("Written status to {self.status_file}: project {self.project.id}, {nsets} sets, {nart} articles"
                     .format(nsets=len(self.setids), nart=len(self.articles), **locals()))

    def _save_with_id_mapping(self, objects):
        for o in objects:
            old_id = o.object.pk
            o.object.pk = None
            if hasattr(o.object, "project_id"):
                o.object.project_id = self.project.id
            o.save()
            yield old_id, o.object.pk

    def check_coders(self):
        emails = {d['coder'] for d in self._get_dicts("codingjobs.jsonl")}
        if any(not e for e in emails):
            raise ValueError("Empty email in coder list")
        users = dict(User.objects.filter(email__in=emails).values_list("email", "pk"))
        if emails - set(users):
            raise ValueError("Users missing in this AmCAT server: {}".format(emails - set(users)))
        return users

    def import_codingjobs(self):
        old_ids, jobs = [], []
        for job in self._get_dicts("codingjobs.jsonl"):
            j = CodingJob(project_id=self.project.id, name=job['name'], archived=job['archived'],
                          insertuser_id=self.user_id, coder_id=self.coders[job['coder']],
                          articleset_id=self.setids[job['articleset']])
            if job['articleschema']:
                j.articleschema_id = self.codingschemas[job['articleschema']]
            if job['unitschema']:
                j.unitschema_id = self.codingschemas[job['unitschema']]
            jobs.append(j)
            old_ids.append(job['pk'])
        jobs = bulk_insert_returning_ids(jobs)
        return {old_id: job.id for (old_id, job) in zip(old_ids, jobs)}

    def import_codings(self):
        cas = self._deserialize("codedarticles.json")
        codedarticles = {}
        for ca in cas:
            cjid = self.codingjobs[ca.object.codingjob_id]
            aid = self.articles[ca.object.article_id]
            try:
                art = CodedArticle.objects.get(codingjob_id=cjid, article_id=aid)
            except CodedArticle.DoesNotExist:
                art = CodedArticle.objects.create(comments=ca.object.comments, status_id=ca.object.status_id,
                                                  codingjob_id=cjid, article_id=aid)
            codedarticles[ca.object.pk] = art
        for a in self._get_dicts("codingvalues.jsonl"):
            ca = codedarticles[a["coded_article_id"]]
            sdict = {(s.parnr, s.sentnr): s.pk for s in sbd.get_or_create_sentences(ca.article)}

            for c in a["codings"]:
                s = c.pop("sentence")
                try:
                    c["sentence_id"] = None if s is None else sdict[tuple(s)]
                except KeyError:
                    logging.warning("Cannot find sentence {ca.article_id}: {s}".format(**locals()))
                    raise
                for v in c["values"]:
                    v["codingschemafield_id"] = self.schemafields[v["codingschemafield_id"]]
                    if "code" in v:
                        v["intval"] = self.codes[v.pop("code")]
            ca.replace_codings(a["codings"])

    def import_codingschemas(self):
        schemas = self._deserialize("codingschemas.json")
        for o in schemas:
            o.m2m_data['highlighters'] = [self.codebooks[cbid] for cbid in o.m2m_data['highlighters']
                                          if cbid in self.codebooks]
        schemafields ={}
        codingschemas = dict(self._save_with_id_mapping(schemas))
        for f in self._deserialize("codingschemafields.json"):
            old_id = f.object.pk
            f.object.pk = None
            f.object.codingschema_id = codingschemas[f.object.codingschema_id]
            if f.object.codebook_id:
                f.object.codebook_id = self.codebooks[f.object.codebook_id]
            f.save()
            schemafields[old_id] = f.object.pk
        return codingschemas, schemafields


    def import_codes(self):
        for c in self._deserialize("codes.json"):
            if not c.object.pk:
                c.save()
            yield c.object.uuid, c.object.pk
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
            yield a['old_id'], aset.id
            if a['favourite']:
                self.project.favourite_articlesets.add(aset)

    def get_sentences(self, articles):
        seen = set(Sentence.objects.filter(article_id__in=articles).values_list("article_id", "parnr", "sentnr"))
        for aid, sentences in articles.items():
            for (parnr, sentnr, sentence) in sentences:
                if (aid, parnr, sentnr) not in seen:
                    yield Sentence(article_id=aid, sentence=sentence, parnr=parnr, sentnr=sentnr)

    def import_sentences(self):
        for i, batch in enumerate(toolkit.splitlist(self._get_dicts("sentences.jsonl"), itemsperbatch=1000)):
            logging.info("Creating sentences for 100 articles, batch {i}".format(**locals()))
            # check existing articles
            articles = {self.articles[d["article_id"]]: d["sentences"] for d in batch}
            sentences = list(self.get_sentences(articles))
            if sentences:
                logging.info("Creating {} sentences".format(len(sentences)))
                Sentence.objects.bulk_create(sentences)

    def import_articles(self):
        def create_articles(batch):
            for a in batch:
                a['oldid_int'] = a.pop('old_id')
            articles = Article.create_articles([Article(project_id=self.project.id, **a) for a in batch])
            self.articles.update({a.get_property('oldid_int'): a.id for a in articles})
            return articles
        hashes = {}
        def create_articles_store_hashes(batch):
            arts = create_articles(batch)
            hashes.update({a.get_property('oldid_int'): a.hash for a in arts})

        # save articles without parents
        for i, batch in enumerate(toolkit.splitlist(self._get_dicts("articles.jsonl"), itemsperbatch=1000)):
            logging.info("Import articles batch {i}".format(**locals()))
            create_articles(batch)

        # Do first pass of articles with parents in batches to avoid potential memory issues
        # (I'm assuming here that the number of 2+ depth children will not be too high)
        todo = []
        hashes = {}  # old_id: hash
        for j, batch in enumerate(toolkit.splitlist(self._get_dicts("articles_with_parents.jsonl"), itemsperbatch=1000)):
            logging.info("Iterating over articles with parents, batch {j}".format(**locals()))
            # sort children, create articles for direct children, remember parent structure for others
            known = []
            for a in batch:
                a['parentid_int'] = a.pop('parent_id')
                if a['parentid_int'] in self.articles:
                    known.append(a)
                else:
                    todo.append(a)
            # retrieve parent hash and create articles for known parents
            if known:
                parents = dict(Article.objects.filter(pk__in={self.articles[a['parentid_int']] for a in known})
                               .values_list("pk", "hash"))
                if len(known) != len(parents):
                    print(parents)
                for a in known:
                    a['parent_hash'] = parents[self.articles[a['parentid_int']]]
                logging.info("Saving {} articles with known parents".format(len(known)))
                create_articles_store_hashes(known)

        logging.info("Direct children saved, {} articles to be dealt with".format(len(todo)))
        # deal with remaining children: (1) save 'real' orphans (ie parent not in this project)
        known_ids = {a["old_id"] for a in todo}
        new_todo, tosave = [], []
        for a in todo:
            parent = a['parentid_int']
            if parent not in known_ids and parent not in self.articles:
                logging.warning("Parent {parent} for article {aid} unknown, removing parent relation"
                                .format(aid=a["old_id"], parent=parent))
                tosave.append(a)
            else:
                new_todo.append(a)
        if tosave:
            logging.info("Saving {} articles without parents".format(len(tosave)))
            create_articles_store_hashes(tosave)

        # (2) make passes through articles until either done or no progress made
        logging.info("Real orphans saved, {} articles todo".format(len(new_todo)))
        while new_todo:
            todo, tosave, new_todo = new_todo, [], []
            for a in todo:
                if a['parentid_int'] in hashes:
                    a['parent_hash'] = hashes[a['parentid_int']]
                    tosave.append(a)
                else:
                    new_todo.append(a)
            if not tosave:
                logging.info("No articles to save, breaking; {} articles todo".format(len(new_todo)))
                break
            logging.info("Saving {} articles with found parents, {} articles todo".format(len(tosave), len(new_todo)))
            create_articles_store_hashes(tosave)

        # store remaining articles without parent, cycles are stupid anyway, right?
        if new_todo:
            logging.info("Data contained cycles, saving remaining {} articles without parents".format(len(new_todo)))
            create_articles(new_todo)

    def import_articlesets_articles(self):
        for i, a in enumerate(self._get_dicts("articlesets_articles.jsonl")):
            logging.info("Adding articles for set {i}: {setid}".format(i=i, setid=a['articleset']))
            if a['articleset'] not in self.setids:
                logging.warning("Missing articleset! {}".format(a['articleset']))
                continue
            setid = self.setids[a['articleset']]
            aids = [self.articles[aid] for aid in a['articles'] if aid in self.articles]
            if len(aids) < len(a['articles']):
                missing = [aid for aid in a['articles'] if aid not in self.articles]
                logging.warning("Not all articles in set were exported, was the project modified during export?"
                                "set: {}, in set: {}, found: {}".format(a['articleset'], len(a['articles']), len(aids)))
                logging.info(str(missing))
            ArticleSet.objects.get(pk=setid).add_articles(aids, add_to_index=False)

    def _get_dicts(self, fn):
        if fn not in self.zipfile.namelist():
            logging.info("Zip contents: {}".format(self.zipfile.namelist()))
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
    result = cli.run_cli()
