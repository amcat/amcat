import argparse
import json
import logging
import tarfile
import getpass
import itertools
from math import ceil
from pathlib import Path
from typing import Iterable, Tuple, Dict

import django

django.setup()
import jsonlines

from amcat.models import Project, Role, ProjectRole, ArticleSet, Article, ArticleSetArticle
from django.contrib.auth.models import User

def create_project(owner: User, project_dict: dict) -> Project:
    logging.info(f"Creating new project {project_dict['name']} (owner: {owner})")
    description = f"{project_dict['description']}\n(imported from amcat.vu.nl project {project_dict['id']})".strip()
    p = Project.objects.create(name=project_dict['name'], description=description, owner=owner, guest_role=None)
    pr = ProjectRole(project=p, user=owner)
    pr.role = Role.objects.get(label='admin')
    pr.save()
    owner.userprofile.favourite_projects.add(p)
    return p


def create_articleset(project: Project, set_dict: dict) -> ArticleSet:
    provenance = f"{set_dict['provenance']} (imported from amcat.vu.nl set {set_dict['id']})"
    return ArticleSet.objects.create(project=project, name=set_dict['name'], provenance=provenance)


def import_articlesets(project: Project, set_dicts: Iterable[dict], n: int) -> Iterable[Tuple[int, ArticleSet]]:
    ndigits = len(str(n))
    for i, set_dict in enumerate(set_dicts):
        logging.info(f"[{i:{ndigits}}/{n}]Creating new article set {set_dict['name']}")
        yield set_dict['id'], create_articleset(project, set_dict)


def chunkify(iterable, chunk_size=100):
    iterator = iter(iterable)
    return itertools.takewhile(bool, (list(itertools.islice(iterator, chunk_size))
                                      for _ in itertools.repeat(None)))


def import_articles(project: Project, articlesets: Dict[int, ArticleSet], art_dicts: Iterable[dict],
                    n: int, chunk_size=1000):
    already_warned = set()
    n = ceil(n/chunk_size)
    ndigits = len(str(n))
    for i, chunk in enumerate(chunkify(art_dicts, chunk_size=chunk_size), start=1):
        logging.info(f"[{i:{ndigits}}/{n}] Importing {len(chunk)} articles")
        sets: Dict[ArticleSet, list] = {aset: [] for aset in articlesets.values()}
        arts = []
        for art in chunk:
            if 'amcatnl_id' in art:
                raise ValueError("Property amcatnl_id already used")
            art['amcatnl_id'] = art.pop("id")
            if 'medium' in art and 'publisher' not in art:
                art['publisher'] = art.pop('medium')
            if 'headline' in art and 'title' not in art:
                art['title'] = art.pop('headline')
            for attr in ['hash', 'projectid', 'mediumid']:
                if attr in art:
                    del art[attr]
            setids = art.pop('sets')
            art['amcatnlsets'] = json.dumps(setids)
            art = {k: v for k, v in art.items() if v is not None}
            a = Article(project=project, **art)
            for setid in setids:
                if setid in articlesets:
                    sets[articlesets[setid]].append(a)
                elif setid not in already_warned:
                    logging.warning(f"Unknown articleset: {setid}")
                    already_warned.add(setid)
            arts.append(a)

        arts = Article.create_articles(arts, add_to_index=False)
        for aset, arts in sets.items():
            if arts:
                ids = [a.id for a in arts]
                aset.add_articles(ids, add_to_index=False)

    # TODO Can be more efficient by reindex in one step
    logging.info("Indexing articles")
    for aset, arts in sets.items():
        if arts:
            logging.info(f".. set {aset}")
            aset.refresh_index(full_refresh=True)


def import_project(username: str, filename: Path):
    owner = User.objects.get(username=username)

    with tarfile.open(args.filename.expanduser()) as f:
        manifest = json.load(f.extractfile("manifest.json"))
        project = create_project(owner, manifest['project'])
        objects = {o['type']: o['n'] for o in manifest['objects']}

        nsets = objects['articleset']
        if nsets:
            logging.info(f"Importing {nsets} articlesets")
            set_dicts = jsonlines.Reader(f.extractfile('articlesets.jsonl'))
            articlesets = dict(import_articlesets(project, set_dicts, n=nsets))

        narts = objects['articles']
        if narts:
            if not nsets:
                raise ValueError("Cannot import articles without article sets")
            art_dicts = jsonlines.Reader(f.extractfile('articles.jsonl'))
            import_articles(project, articlesets, art_dicts, n=narts)


parser = argparse.ArgumentParser()
parser.add_argument('filename', type=Path)
parser.add_argument('--owner', type=Path)
args = parser.parse_args()
logging.basicConfig(level=logging.INFO, format='[%(asctime)s %(name)-12s %(levelname)-5s] %(message)s')

import_project(username=args.owner or getpass.getuser(),
               filename=args.filename.expanduser())
