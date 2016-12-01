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
Simple regex-based sentence boundary detection
"""

import functools
import collections
import re

from amcat.models import Article
from amcat.models.sentence import Sentence

abbrevs = ["ir", "mr", "dr", "dhr", "ing", "drs", "mrs", "sen", "sens", "gov", "st",
           "jr", "rev", "vs", "gen", "adm", "sr", "lt", "sept"]
months = ["Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


PARAGRAPH_RE = re.compile(r"\n\s*\n[\s\n]*")


@functools.lru_cache()
def get_split_regex():
    # [Martijn] Documentation??
    lenmap = collections.defaultdict(list)
    for a in abbrevs + months:
        lenmap[len(a)].append(a)
        lenmap[len(a)].append(a.title())
    expr = r"(?<!\b[A-Za-z])"
    for x in lenmap.values():
        expr += r"(?<!\b(?:%s))" % "|".join(x)
    expr += r"[\.?!](?!\.\.)(?<!\.\.)(?!\w|,)(?!\s[a-z])|\n\n"
    expr += r"|(?<=%s)\. (?=[^\d])" % "|".join(months)
    return re.compile(expr)


def get_or_create_sentences(article):
    """
    Split the given article object into sentences and save the sentences models
    to the database. Returns a list of the resulting Sentence objects.

    This function (as opposed to create_sentences) does not error when an article
    is already split.
    """
    if not article.sentences.exists():
        create_sentences(article)
    return article.sentences.all()


def _get_paragraphs(article: Article):
    # Title
    yield article.title

    # Byline
    properties = article.get_properties()
    if "byline" in properties:
        yield properties["byline"]

    # Text splitted on white lines
    yield from iter(PARAGRAPH_RE.split(article.text.strip()))


def _create_sentences(article: Article):
    for parnr, par in enumerate(_get_paragraphs(article)):
        for sentnr, sent in enumerate(split(par)):
            yield Sentence(parnr=parnr + 1, sentnr=sentnr + 1, article=article, sentence=sent)


def create_sentences(article):
    """
    Split the given article object into sentences and save the sentences models
    to the database. Returns a list of the resulting Sentence objects.

    If you can, cache properties title, byline and text.
    """
    sents = tuple(_create_sentences(article))
    Sentence.objects.bulk_create(sents)
    return sents


def split(text):
    """
    Split the text into sentences and yield the sentence strings
    """
    text = re.sub("\n\n+", "\n\n", text)
    text = text.replace(".'", "'.")

    sentences = get_split_regex().split(text)
    sentences = (s.strip() for s in sentences)
    sentences = (s for s in sentences if s)
    sentences = (re.sub("\s+", " ", s) for s in sentences)
    return sentences
