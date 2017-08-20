import json
from zipfile import ZipFile
import logging

from django import forms

import django;
django.setup()

from amcat.models.article import Article
from amcat.tools import toolkit
from amcat.models.articleset import ArticleSet
from amcat.scripts.script import Script


class ImportProject(Script):
    class options_form(forms.Form):
        file = forms.FileField()

    def _run(self, file):
        from amcat.models import Project
        self.setids = {}  # old_id -> new_id
        self.articles = {}  # old_id -> new_id
        self.zipfile = ZipFile(file.file.name)
        self.project = Project.objects.create(name=file.file.name, owner_id=1)
        self.import_articlesets()
        self.import_articles()
        self.import_articlesets_articles()
        logging.info("Done!")

    def _get_dicts(self, fn):
        logging.info("Reading {fn}".format(**locals()))
        for line in self.zipfile.open(fn):
            yield json.loads(line.decode("utf-8"))

    def import_articlesets(self):
        for a in self._get_dicts("articlesets.json"):
            aset = ArticleSet.objects.create(project=self.project, name=a['name'], provenance=a['provenance'])
            self.setids[a['old_id']] = aset.id
            if a['favourite']:
                self.project.favourite_articlesets.add(aset)

    def import_articles(self):
        for i, batch in enumerate(toolkit.splitlist(self._get_dicts("articles.json"), itemsperbatch=1000)):
            logging.info("Import articles batch {i}".format(**locals()))
            uuids = {a['properties']['uuid'] : a.pop('old_id') for a in batch}
            articles = Article.create_articles([Article(project_id=self.project.id, **a) for a in batch])
            self.articles.update({uuids[a.get_property('uuid')]: a.id for a in articles})

    def import_articlesets_articles(self):
        for a in self._get_dicts("articlesets_articles.json"):
            aids = [self.articles[aid] for aid in a['articles']]
            setid = self.setids[a['articleset']]
            ArticleSet.objects.get(pk=setid).add_articles(aids)


if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()