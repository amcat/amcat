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

"""
This controller handles all views meant to be used within a project's
scope. The general structure is:

    - (Multiple) projects overview
    - Single project overview-tabs
    - Project management
    - Codebooks

"""

import json
import itertools
import datetime

from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.db import transaction
from django.utils.datastructures import SortedDict

from api.rest.resources import ArticleMetaResource
from api.rest.resources import CodingSchemaResource
from api.rest.resources import ProjectRoleResource
from api.rest.resources import CodingSchemaFieldResource
from api.rest.resources import PluginResource, ScraperResource
from api.rest.datatable import Datatable
from amcat.models import Project, Language, Role, ProjectRole, Code, Label, Article
from amcat.models import CodingJob, Codebook, CodebookCode, CodingSchema
from amcat.models import CodingSchemaField, ArticleSet, Plugin
from amcat.scripts.actions.add_project import AddProject
from amcat.scripts.article_upload.upload import UploadScript
from amcat.scripts.actions.get_codingjob_results import CodingjobListForm, EXPORT_FORMATS
from navigator import forms
from navigator.utils.auth import check, check_perm
from navigator.utils.action import ActionHandler
from amcat.scripts.actions.get_codingjob_results import GetCodingJobResults
from amcat.scripts.output.csv_output import TableToSemicolonCSV
from amcat.models.project import LITTER_PROJECT_ID
from amcat.models.user import User
from amcat.models.user import LITTER_USER_ID
from api.rest.resources.codebook import CodebookHierarchyResource


PROJECT_MENU = None
PROJECT_READ_WRITE = Role.objects.get(projectlevel=True, label="read/write").id

import logging; log = logging.getLogger(__name__)


def table_view(request, context, table, selected=None, overview=False,
               menu=PROJECT_MENU, template=None, **kargs):
    """
    Renders simple page containing only a table, within a projects tab.

    @param context: Indicates scope of the tabs.
    @type context: amcat.models.Project

    @param table: table to render
    @type table: Datatables object

    @param selected: which tab to be selected.
    @type selected: None, str

    @param overview: indicates whether 'add project' link should be shown
    @type overview: bool
    """
    kargs.update(locals())
    return render(request, template or "navigator/project/table.html", kargs)

# Whether or not a menu-item is selected is determined by its module. Importing
# views from other modules prevents wrongly unselected items, while preserving
# modularity.

@check(Article)
def sentences(request, art, projectid=None):
    ctx = dict(article=art)

    if projectid is not None:
        ctx['menu'] = PROJECT_MENU
        ctx['context'] = Project.objects.get(id=projectid)
    
    return render(request, "navigator/article/view.html", ctx)

def _codingjob_export(results, codingjob, filename):
    results = TableToSemicolonCSV().run(results)
    filename = filename.format(codingjob=codingjob, now=datetime.datetime.now())
    response = HttpResponse(content_type='text/csv', status=201)
    response['Content-Disposition'] = 'attachment; filename="{filename}"'.format(**locals())
    response.write(results)
    return response

@check(CodingJob, args_map={'codingjob' : 'id'}, args='codingjob')
@check(Project, args_map={'project' : 'id'}, args='project')
def codingjob_unit_export(request, project, codingjob):
    results = GetCodingJobResults(job=codingjob.id, unit_codings=True, deserialize_codes=True).run()
    return _codingjob_export(results, codingjob, "{codingjob}, units, {now}.csv")

@check(CodingJob, args_map={'codingjob' : 'id'}, args='codingjob')
@check(Project, args_map={'project' : 'id'}, args='project')
def codingjob_article_export(request, project, codingjob):
    results = GetCodingJobResults(job=codingjob.id, unit_codings=False, deserialize_codes=True).run()
    return _codingjob_export(results, codingjob, "{codingjob}, articles, {now}.csv")

@check(Project, args_map={'project' : 'id'}, args='project')
def codingjob_export_select(request, project):
    form = CodingjobListForm(request.POST or None, project=project)

    if form.is_valid():
        url = reverse(codingjob_export_options, args=[project.id])
        jobs = form.cleaned_data["codingjobs"]
        if len(jobs) < 100:
            codingjobs_url = "&".join("codingjobs={}".format(c.id) for c in jobs)
        else:
            codingjobs_url = "use_session=1"
            request.session['export_job_ids'] = json.dumps([c.id for c in jobs])
            
        return redirect("{url}?export_level={level}&{codingjobs_url}"
                        .format(level=form.cleaned_data["export_level"], **locals()))


    return render(request, 'navigator/project/export_select.html', locals())

@check(Project, args_map={'project' : 'id'}, args='project')
def codingjob_export_options(request, project):
    if request.GET.get("use_session"):
        jobs = json.loads(request.session['export_job_ids'])
    else:
        jobs = request.GET.getlist("codingjobs")
    level = int(request.GET["export_level"])
    form = GetCodingJobResults.options_form(
        request.POST or None, project=project, codingjobs=jobs, export_level=level,
        initial=dict(codingjobs=jobs, export_level=level)
    )

    
    
    sections = SortedDict() # section : [(id, field, subfields) ..]
    subfields = {} # fieldname -> subfields reference

    for name in form.fields:
        if form[name].is_hidden:
            continue
        prefix = name.split("_")[0]
        section = {"schemafield" : "Field options", "meta" : "Metadata options"}.get(prefix, "General options")

        if prefix == "schemafield" and not name.endswith("_included"):
            continue
        subfields[name] = []
        sections.setdefault(section, []).append((name, form[name], subfields[name]))
        form[name].subfields = []

    # sort coding fields
    codingfields = sorted(sections["Field options"])
    sections["Field options"].sort()
    
    for name in form.fields: # add subordinate fields        
        prefix = name.split("_")[0]
        if prefix == "schemafield" and not name.endswith("_included"):
            subfields[name.rsplit("_", 1)[0] + "_included"].append((name, form[name]))

    for flds in subfields.values():
        flds.sort()
            
    if form.is_valid():
        results = GetCodingJobResults(form).run()

        eformat = {f.label : f for f in EXPORT_FORMATS}[form.cleaned_data["export_format"]]
        
        if eformat.mimetype is not None:
            if len(jobs) > 3:
                jobs = jobs[:3] + ["etc"]
            filename = "Codingjobs {j} {now}.{ext}".format(j=",".join(str(j) for j in jobs), now=datetime.datetime.now(), ext=eformat.label)
            response = HttpResponse(content_type=eformat.mimetype, status=200)
            response['Content-Disposition'] = 'attachment; filename="{filename}"'.format(**locals())
            response.write(results)
            return response

    return render(request, 'navigator/project/export_options.html', locals())

@check(Codebook, args='id', action='delete')
@check(Project, args_map={'projectid' : 'id'}, args='projectid')
def codebook_delete(request, project, codebook):
    codebook.project = Project.objects.get(id=LITTER_PROJECT_ID)
    codebook.save()

    request.session['deleted_codebook'] = True
    return redirect(reverse("project-codebooks", args=[project.id]))


@check(Project, args_map={'project' : 'id'}, args='project')
@check(Codebook, args_map={'codebook' : 'id'}, args='codebook', action="update")
def save_name(request, codebook, project):
    codebook.name = request.POST.get("codebook_name")
    codebook.save()

    return HttpResponse(status=200)

@transaction.commit_on_success
@check(Project, args_map={'project' : 'id'}, args='project')
@check(Codebook, args_map={'codebook' : 'id'}, args='codebook', action="update")
def save_changesets(request, codebook, project):
    moves = json.loads(request.POST.get("moves", "[]"))
    hides = json.loads(request.POST.get("hides", "[]"))
    reorders = json.loads(request.POST.get("reorders", "[]"))

    codebook.cache()

    # Keep a list of changed codebookcodes
    changed_codes = tuple(itertools.chain(
        set([h["code_id"] for h in hides]),
        set([r["code_id"] for r in reorders]),
        set(itertools.chain.from_iterable(m.values() for m in moves))
    ))

    # Save reorders
    for reorder in reorders:
        ccode = codebook.get_codebookcode(codebook.get_code(reorder["code_id"]))
        ccode.ordernr = reorder["ordernr"]

    # Save all hides
    for hide in hides:
        ccode = codebook.get_codebookcode(codebook.get_code(hide["code_id"]))
        ccode.hide = hide.get("hide", False)

    # Save all moves
    for move in moves:
        ccode = codebook.get_codebookcode(codebook.get_code(move["code_id"]))
        ccode.parent = None

        if move["new_parent"] is None:
            continue

        new_parent = codebook.get_code(move["new_parent"])
        ccode.parent = new_parent

    # Commit all changes
    for code_id in changed_codes:
        ccode = codebook.get_codebookcode(codebook.get_code(code_id))

        # Saving a codebookcode triggers a validation function which needs
        # the codebookcode's codebook's codebookcodes.
        ccode._codebook_cache = codebook
        ccode.save(validate=False)

    # Check for any cycles. 
    CodebookHierarchyResource.get_tree(Codebook.objects.get(id=codebook.id), include_labels=False)

    # No error thrown, so no cycles detected
    return HttpResponse(status=200)

@check(Project, args_map={'project' : 'id'}, args='project')
@check(Codebook, args_map={'codebook' : 'id'}, args='codebook', action="update")
def save_labels(request, codebook, project):
    """
    View called by code-editor to store new labels. It requests
    two values in POST:

     - labels: an (json-encoded) list with label-objects
     - code: an (json-encoded) code object to which the labels belong

    If an extra value 'parent' is included, this view will create
    a new code and adds the given labels to it.
    """
    labels = json.loads(request.POST['labels'])

    if "parent" in request.POST:
        code = Code.objects.create()
        parent = json.loads(request.POST["parent"])

        CodebookCode.objects.create(
            parent=None if parent is None else Code.objects.get(id=parent),
            code=code, codebook=codebook
        )

    else:
        code = Code.objects.get(id=int(request.POST['code']))

    # Get changed, deleted and new labels
    changed_labels_map = { int(lbl.get("id")) : lbl for lbl in labels if lbl.get("id") is not None}
    changed_labels = set(Label.objects.filter(id__in=changed_labels_map.keys()))

    created_labels = [Label(
        language=Language.objects.get(id=lbl.get("language")), code=code, label=lbl["label"]
    ) for lbl in labels if lbl.get("id", None) is None]

    current_labels = set(code.labels.all())
    deleted_labels = current_labels - changed_labels

    # Deleting requested labels
    for lbl in deleted_labels:
        lbl.delete()

    # Create new labels
    Label.objects.bulk_create(created_labels)

    # Update existing labels
    for label in changed_labels:
        label.language = Language.objects.get(id=changed_labels_map[label.id]["language"])
        label.label = changed_labels_map[label.id]["label"]
        label.save()

    content = json.dumps(dict(code_id=code.id))
    return HttpResponse(content=content, status=201, content_type="application/json")

