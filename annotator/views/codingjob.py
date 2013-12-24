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
from functools import partial

import json
import logging
from django.core.exceptions import PermissionDenied
from django.db import transaction, connection
from django.db.models import sql

from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from django.core.urlresolvers import reverse
import itertools

from amcat.models import CodingJob, Project, Article, CodingValue, Coding

log = logging.getLogger(__name__)

def index(request, project_id, codingjob_id):
    """returns the HTML for the main annotator page"""
    return render(request, "annotator/codingjob.html", {
        'codingjob': CodingJob.objects.get(id=codingjob_id),
        'project': Project.objects.get(id=project_id),
        'coder' : request.user,
    })

def _to_coding(codingjob, article, coding):
    """
    Takes a dictionary with keys 'sentence_id', 'status', 'comments' and creates
    an (unsaved) Coding object.

    @type codingjob: CodingJob
    @type article: Article
    @type coding: dict
    """
    return Coding(
        codingjob=codingjob, article=article,
        sentence_id=coding["sentence_id"], status_id=coding["status_id"],
        comments=coding["comments"]
    )

def _to_codingvalue(coding, codingvalue):
    """
    Takes a dictionary with keys 'codingschemafield_id', 'intval', 'strval' and creates
    an (unsaved) CodingValue object.

    @type coding: Coding
    @type codingvalue: dict
    """
    return CodingValue(
        field_id=codingvalue["codingschemafield_id"], intval=codingvalue["intval"],
        strval=codingvalue["strval"], coding=coding
    )

def _to_codingvalues(coding, values):
    """
    Takes an iterator with codingvalue dictionaries (see _to_coding) and a coding,
    and returns an iterator with CodingValue's.
    """
    return map(partial(_to_codingvalue, coding), values)


def save(request, project_id, codingjob_id, article_id):
    """
    Big fat warning: we don't do server side validation for the codingvalues. We
    do check if the codingjob and logged in user correspond, but it's the users
    responsibilty to send correct data (we don't care!).
    """
    project = Project.objects.get(id=project_id)
    codingjob = CodingJob.objects.select_related("articleset").get(id=codingjob_id)
    article = Article.objects.only("id").get(id=article_id)

    if codingjob.project_id != project.id:
        raise PermissionDenied("Given codingjob ({codingjob}) does not belong to project ({project})!".format(**locals()))

    if codingjob.coder != request.user:
        raise PermissionDenied("Only {request.user} can edit this codingjob.".format(**locals()))

    if not codingjob.articleset.articles.filter(id=article_id).exists():
        raise PermissionDenied("{article} not in {codingjob}.".format(**locals()))

    try:
        codings = json.loads(request.body)
    except ValueError:
        return HttpResponseBadRequest("Invalid JSON in POST body")

    article_coding = codings["article_coding"]
    sentence_codings = codings["sentence_codings"]

    with transaction.atomic():
        to_coding = partial(_to_coding, codingjob=codingjob, article=article)

        # Updating tactic: delete all existing codings and codingvalues, then insert
        # the new ones. This prevents calculating a delta, and confronting the
        # database with (potentially) many update queries.
        CodingValue.objects.filter(coding__codingjob=codingjob, coding__article=article).delete()
        Coding.objects.filter(codingjob=codingjob, article=article).delete()

        new_codings = list(itertools.chain([article_coding], sentence_codings))
        new_coding_objects = map(partial(_to_coding, codingjob, article), new_codings)

        # Saving each coding is pretty inefficient, but Django doesn't allow retrieving
        # id's when using bulk_create. See Django ticket #19527.
        if connection.vendor == "postgresql":
            query = sql.InsertQuery(Coding)
            query.insert_values(Coding._meta.fields[1:], new_coding_objects)
            raw_sql, params = query.sql_with_params()[0]
            new_coding_objects = Coding.objects.raw("%s %s" % (raw_sql, "RETURNING coding_id"), params)
        else:
            # Do naive O(n) approach
            for coding in new_coding_objects:
                coding.save()

        coding_values = itertools.chain.from_iterable(
            _to_codingvalues(co, c["values"]) for c, co in itertools.izip(new_codings, new_coding_objects)
        )

        CodingValue.objects.bulk_create(coding_values)

    return HttpResponse(status=201)

def redirect(request, codingjob_id):
    cj = CodingJob.objects.get(id=codingjob_id)
    return HttpResponseRedirect(reverse(index, kwargs={
        "codingjob_id" : codingjob_id, "project_id" : cj.project_id
    }))
