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
from amcat.models.authorisation import ROLE_PROJECT_ADMIN


from amcat.models import CodingJob, Project, Article, CodingValue, Coding, CodedArticle

log = logging.getLogger(__name__)


def index(request, project_id, codingjob_id):
    """returns the HTML for the main annotator page"""
    return render(request, "annotator/codingjob.html", {
        'codingjob': CodingJob.objects.get(id=codingjob_id),
        'project': Project.objects.get(id=project_id),
        'coder' : request.user,
        'annotator': True
    })


def save(request, project_id, codingjob_id, coded_article_id):
    """
    Big fat warning: we don't do server side validation for the codingvalues. We
    do check if the codingjob and logged in user correspond, but it's the users
    responsibilty to send correct data (we don't care!).
    """
    coded_article = CodedArticle.objects.select_related("codingjob__project", "codingjob", "article").get(id=coded_article_id)

    # sanity checks
    if coded_article.codingjob.project_id != int(project_id):
        raise PermissionDenied("Given codingjob ({coded_article.codingjob}) does not belong to project ({coded_article.codingjob.project})!".format(**locals()))
    if coded_article.codingjob_id != int(codingjob_id):
        raise PermissionDenied("CodedArticle has codingjob_id={coded_article.codingjob_id} but {codingjob_id} given in url!")

    if coded_article.codingjob.coder_id != request.user.id:
        # the user is not the assigned coder. Is s/he project admin?
        if not  coded_article.codingjob.project.has_role(request.user, ROLE_PROJECT_ADMIN):
            raise PermissionDenied("Only {request.user} or project admins can edit this codingjob.".format(**locals()))

    try:
        codings = json.loads(request.body.decode())
    except ValueError:
        return HttpResponseBadRequest("Invalid JSON in POST body")

    coded_article.status_id = codings["coded_article"]["status_id"]
    coded_article.comments = codings["coded_article"]["comments"]
    coded_article.save()

    new_coding_objects, new_coding_values = coded_article.replace_codings(codings["codings"])

    status = {
        "saved_codings": len(new_coding_objects),
        "saved_values": len(new_coding_values)
    }

    return HttpResponse(status=201, content=json.dumps(status))


def redirect(request, codingjob_id):
    cj = CodingJob.objects.get(id=codingjob_id)
    return HttpResponseRedirect(reverse("annotator:annotator-codingjob", kwargs={
        "codingjob_id" : codingjob_id, "project_id" : cj.project_id
    }))
