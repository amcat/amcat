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

from amcat.models import CodingJob, Project, Article, CodingValue, Coding, CodedArticle

log = logging.getLogger(__name__)

def index(request, project_id, codingjob_id):
    """returns the HTML for the main annotator page"""
    return render(request, "annotator/codingjob.html", {
        'codingjob': CodingJob.objects.get(id=codingjob_id),
        'project': Project.objects.get(id=project_id),
        'coder' : request.user,
    })

def save(request, project_id, codingjob_id, article_id):
    """
    Big fat warning: we don't do server side validation for the codingvalues. We
    do check if the codingjob and logged in user correspond, but it's the users
    responsibilty to send correct data (we don't care!).
    """
    project = Project.objects.get(id=project_id)
    codingjob = CodingJob.objects.select_related("articleset").get(id=codingjob_id)
    article = Article.objects.only("id").get(id=article_id)
    coded_article = CodedArticle.objects.get(article__id=article_id, codingjob__id=codingjob_id).select_related("codingjob", "article")

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
    coded_article.replace_codings(itertools.chain([article_coding], sentence_codings))
    return HttpResponse(status=201)

def redirect(request, codingjob_id):
    cj = CodingJob.objects.get(id=codingjob_id)
    return HttpResponseRedirect(reverse(index, kwargs={
        "codingjob_id" : codingjob_id, "project_id" : cj.project_id
    }))
