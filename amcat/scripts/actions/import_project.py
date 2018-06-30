import json
import os
import tempfile
from zipfile import ZipFile
import logging

from django import forms
from django.core import serializers

from amcat.scripts.tools import cli
from amcat.models.authorisation import ProjectRole, Role
from amcat.models.user import create_user
from amcat.models import Article, ArticleSet, Project, Label, CodebookCode, CodedArticle, User, CodingJob, Sentence
from amcat.tools import toolkit
from amcat.scripts.script import Script
from amcat.tools.amcates import ES
from amcat.tools.djangotoolkit import bulk_insert_returning_ids


def _load_sentences(sentences, target = None):
    if target is None:
        target = {}
    for (aid, par, sent, sent_id) in sentences:
        target.setdefault(aid, {})[par, sent] = sent_id
    return target


class ImportStatus:
    """Keep track of import status and id mappings"""
    def __init__(self, status_file=None):
        if status_file:
            logging.info("Reading status from {status_file}".format(**locals()))
            status = json.load(open(status_file)) if os.path.exists(status_file) else {}
            self._status_file = status_file
        else:
            status = {}
            _, self._status_file = tempfile.mkstemp(suffix=".json", prefix="import_status")

        def _intkeys(key):
            return {int(k): v for (k, v) in status[key].items()} if key in status else {}
        self.project = Project.objects.get(pk=status['project']) if 'project' in status else None
        # Mappings of old_id --> new_id:
        self.setids = _intkeys('setids')
        self.articles = _intkeys('articles')
        self.codebooks = _intkeys('codebooks')
        self.codingschemas = _intkeys('codingschemas')
        self.schemafields = _intkeys('schemafields')
        self.codingjobs = _intkeys('codingjobs')
        # boolean flags that items have been imported:
        self.articlesets_articles = status.get('articlesets_articles', False)
        self.codebookcodes = status.get('codebookcodes', False)
        self.codings = status.get('codings', False)
        # other mappings:
        self.sentences = _load_sentences(status.get('sentences', []))  # {article_id : {(par, sent): sent.id}}
        self.codes = status.get('codes', {})  # uuid -> id
        self.users = status.get('users', {})  # email -> id

    def set(self, **kargs):
        for k, v in kargs.items():
            self.__setattr__(k, v)
        self.save()

    def save(self):
        def _save_sentences(sentences):
            """dict to tuple (json dicts require str keys, so no good)"""
            for aid, sents in sentences.items():
                yield from ((aid, par, sent, sentid) for ((par, sent), sentid) in sents.items())
        status = {k: v for (k, v) in self.__dict__.items() if not k.startswith("_")}
        status['project'] = self.project.id
        status['sentences'] = list(_save_sentences(status.pop('sentences')))
        json.dump(status, open(self._status_file, "w"))
        logging.info("Written status to {self._status_file}".format(**locals()))


class ImportProject(Script):
    class options_form(forms.Form):
        file = forms.FileField()
        user = forms.ModelChoiceField(queryset=User.objects.all(), help_text="Import project as this user",
                                      required=False)
        status_file = forms.CharField(required=False, help_text="Continue from partial import")

    def _run(self, file, user, status_file=None):
        self.status = ImportStatus(status_file)
        self.zipfile = ZipFile(file.file.name)
        if not self.status.project:
            self.status.set(project=Project.objects.create(name=file.file.name, owner_id=(user.pk if user else 1)))
        if not self.status.users:
            self.status.set(users=dict(self.import_users()))

        if not self.status.setids:
            self.status.set(setids=dict(self.import_articlesets()))
        if not self.status.articles:
            self.import_articles()
            self.status.save()

        if not self.status.articlesets_articles:
            self.import_articlesets_articles()
            self.status.set(articlesets_articles=True)
        if not self.status.codes:
            self.status.set(codes=dict(self.import_codes()))

        if not self.status.codebooks:
            self.status.set(codebooks=self.import_codebooks())
        if not self.status.codebookcodes:
            self.import_codebookcodes()
            self.status.set(codebookcodes=True)
        if not self.status.codingschemas:
            codingschemas, schemafields = self.import_codingschemas()
            self.status.set(codingschemas=codingschemas, schemafields=schemafields)
        if not self.status.codingjobs:
            self.status.set(codingjobs=dict(self.import_codingjobs()))
        if not self.status.sentences:
            self.status.set(sentences=self.import_sentences())
        if not self.status.codings:
            self.import_codings()
            self.status.set(codings=True)
        logging.info("Adding articles to index")
        ES().add_articles(self.status.articles.values())

        logging.info("Done!")

    def _save_with_id_mapping(self, objects):
        for o in objects:
            old_id = o.object.pk
            o.object.pk = None
            if hasattr(o.object, "project_id"):
                o.object.project_id = self.status.project.id
            o.save()
            yield old_id, o.object.pk

    def import_codingjobs(self):
        old_ids, jobs = [], []
        for job in self._get_dicts("codingjobs.jsonl"):
            j = CodingJob(project_id=self.status.project.id, name=job['name'], archived=job['archived'],
                          insertuser_id=self.status.project.owner.id, coder_id=self.status.users[job['coder']],
                          articleset_id=self.status.setids[job['articleset']])
            if job['articleschema']:
                j.articleschema_id = self.status.codingschemas[job['articleschema']]
            if job['unitschema']:
                j.unitschema_id = self.status.codingschemas[job['unitschema']]
            jobs.append(j)
            old_ids.append(job['pk'])
        jobs = bulk_insert_returning_ids(jobs)
        return {old_id: job.id for (old_id, job) in zip(old_ids, jobs)}

    def import_codings(self):
        cas = self._deserialize("codedarticles.json")
        codedarticles = {}
        for ca in cas:
            cjid = self.status.codingjobs[ca.object.codingjob_id]
            aid = self.status.articles[ca.object.article_id]
            try:
                art = CodedArticle.objects.get(codingjob_id=cjid, article_id=aid)
            except CodedArticle.DoesNotExist:
                art = CodedArticle.objects.create(comments=ca.object.comments, status_id=ca.object.status_id,
                                                  codingjob_id=cjid, article_id=aid)
            codedarticles[ca.object.pk] = art
        for a in self._get_dicts("codingvalues.jsonl"):
            ca = codedarticles[a["coded_article_id"]]
            sdict = self.status.sentences.get(ca.article_id, {})
            for c in a["codings"]:
                parsent = c.pop("sentence")
                try:
                    c["sentence_id"] = None if parsent is None else sdict[tuple(parsent)]
                except KeyError:
                    logging.warning("Cannot find sentence {ca.article_id}: {parsent}"
                                    "(old codedarticle id: {caid}), creating dummy sentence"
                                    .format(caid=a["coded_article_id"], **locals()))
                    s = Sentence.objects.create(article_id=ca.article_id, parnr=parsent[0], sentnr=parsent[1],
                                                sentence="<unknown sentence>")
                    c["sentence_id"] = s.id
                    self.status.sentences.setdefault(ca.article_id, {})[tuple(parsent)] = s.id
                for v in c["values"]:
                    v["codingschemafield_id"] = self.status.schemafields[v["codingschemafield_id"]]
                    if "code" in v:
                        v["intval"] = self.status.codes[v.pop("code")]
            ca.replace_codings(a["codings"], check_schemafields=False)

    def import_codingschemas(self):
        schemas = self._deserialize("codingschemas.json")
        for o in schemas:
            o.m2m_data['highlighters'] = [self.status.codebooks[cbid] for cbid in o.m2m_data['highlighters']
                                          if cbid in self.status.codebooks]
        schemafields = {}
        codingschemas = dict(self._save_with_id_mapping(schemas))
        for f in self._deserialize("codingschemafields.json"):
            old_id = f.object.pk
            f.object.pk = None
            f.object.codingschema_id = codingschemas[f.object.codingschema_id]
            if f.object.codebook_id:
                f.object.codebook_id = self.status.codebooks[f.object.codebook_id]
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
            c.codebook_id = self.status.codebooks[c.codebook_id]
            c.pk = None
        CodebookCode.objects.bulk_create(cbcodes)

    def import_articlesets(self):
        for a in self._get_dicts("articlesets.jsonl"):
            aset = ArticleSet.objects.create(project=self.status.project, name=a['name'], provenance=a['provenance'])
            yield a['old_id'], aset.id
            if a['favourite']:
                self.status.project.favourite_articlesets.add(aset)

    def get_sentences(self, articles, sentences):
        for aid, sents in articles.items():
            for (parnr, sentnr, sentence) in sents:
                if (parnr, sentnr) not in sentences.get(aid, {}):
                    yield Sentence(article_id=aid, sentence=sentence, parnr=parnr, sentnr=sentnr)

    def import_sentences(self):
        sentences = {}  # aid -> {par, sent -> sent_id}
        for i, batch in enumerate(toolkit.splitlist(self._get_dicts("sentences.jsonl"), itemsperbatch=1000)):
            logging.info("Creating sentences for 1000 articles, batch {i}".format(**locals()))
            # check existing articles
            articles = {self.status.articles[d["article_id"]]: d["sentences"] for d in batch}
            _load_sentences(Sentence.objects.filter(article_id__in=articles)
                            .values_list("article_id", "parnr", "sentnr", "pk")
                            , target=sentences)
            to_add = list(self.get_sentences(articles, sentences))
            if to_add:
                logging.info("Creating {} sentences".format(len(to_add)))
                added = ((s.article_id, s.parnr, s.sentnr, s.pk) for s in bulk_insert_returning_ids(to_add,
                                                                                                    fields=["*"]))
                _load_sentences(added, target=sentences)
                sentences.update(added)
        return sentences

    def import_articles(self):
        def create_articles(batch):
            for a in batch:
                a['oldid_int'] = a.pop('old_id')
                if a['text'] == '': a['text'] = '-'
                if a['title'] == '': a['title'] = '-'
            articles = Article.create_articles([Article(project_id=self.status.project.id, **a) for a in batch])
            self.status.articles.update({a.get_property('oldid_int'): a.id for a in articles})
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
        for j, batch in enumerate(toolkit.splitlist(self._get_dicts("articles_with_parents.jsonl"),
                                                    itemsperbatch=1000)):
            logging.info("Iterating over articles with parents, batch {j}".format(**locals()))
            # sort children, create articles for direct children, remember parent structure for others
            known = []
            for a in batch:
                a['parentid_int'] = a.pop('parent_id')
                if a['parentid_int'] in self.status.articles:
                    known.append(a)
                else:
                    todo.append(a)
            # retrieve parent hash and create articles for known parents
            if known:
                parents = dict(Article.objects.filter(pk__in={self.status.articles[a['parentid_int']] for a in known})
                               .values_list("pk", "hash"))
                for a in known:
                    a['parent_hash'] = parents[self.status.articles[a['parentid_int']]]
                logging.info("Saving {} articles with known parents".format(len(known)))
                create_articles_store_hashes(known)

        logging.info("Direct children saved, {} articles to be dealt with".format(len(todo)))
        # deal with remaining children: (1) save 'real' orphans (ie parent not in this project)
        known_ids = {a["old_id"] for a in todo}
        new_todo, tosave = [], []
        for a in todo:
            parent = a['parentid_int']
            if parent not in known_ids and parent not in self.status.articles:
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
            if a['articleset'] not in self.status.setids:
                logging.warning("Missing articleset! {}".format(a['articleset']))
                continue
            setid = self.status.setids[a['articleset']]
            aids = [self.status.articles[aid] for aid in a['articles'] if aid in self.status.articles]
            if len(aids) < len(a['articles']):
                missing = [aid for aid in a['articles'] if aid not in self.status.articles]
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

    def import_users(self):
        for u in self._get_dicts("users.jsonl"):
            # get or create user
            try:
                user = User.objects.get(email=u['email'])
            except User.DoesNotExist:
                user = create_user(u['username'], u['first_name'], u['last_name'], u['email'])
                user.password = u['password']
                user.save()
            # add user to project
            role = Role.objects.get(label=u['role'])
            if not ProjectRole.objects.filter(project=self.status.project, user=user).exists():
                ProjectRole.objects.create(project=self.status.project, user=user, role=role)
            yield u['email'], user.id
        self.check_coders()

    def check_coders(self):
        emails = {d['coder'] for d in self._get_dicts("codingjobs.jsonl")}
        if any(not e for e in emails):
            raise ValueError("Empty email in coder list")
        users = dict(User.objects.filter(email__in=emails).values_list("email", "pk"))
        if emails - set(users):
            raise ValueError("Users missing in this AmCAT server: {}".format(emails - set(users)))


if __name__ == '__main__':
    cli.run_cli()
