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


@check(Project)
def upload_article(request, project):
    plugin_type = UploadScript.get_plugin_type()
    #scripts = (Datatable(PluginResource, rowlink="./upload-articles/{id}")
    #           .filter(plugin_type=plugin_type)
    #           .hide('id', 'class_name', 'plugin_type'))
    
    scripts = (Datatable(PluginResource, rowlink="./upload-articles/{id}")
               .filter(plugin_type=plugin_type).hide('id', 'plugin_type'))

    can_create_plugin = False#Plugin.can_create(request.user)

    return table_view(request, project, scripts, selected='article sets',
            template='navigator/project/upload.html', can_create_plugin=can_create_plugin,
                      plugin_type=plugin_type)

@check(Project)
def scrape_articles(request, project):
    scripts = (Datatable(ScraperResource, rowlink="./scrape-articles/{id}").hide('module', 'class_name', 'username', 'password', 'run_daily', 'articleset'))

    return table_view(request, project, scripts, selected='article sets',
                      template='navigator/project/scrape.html')

@check(Project, args_map={'project' : 'id'}, args='project')
@check(Plugin, args_map={'plugin' : 'id'}, args='plugin')
def upload_article_action(request, plugin, project):
    script_class = plugin.get_class()
    form = script_class.get_empty_form(project=project, post=request.POST or None, files=request.FILES)

    if request.POST:
        if form.is_valid():
            script = script_class(form)
            try:
                created_articles = script.run()
            except Exception, e:
                log.exception(e)
                scraper_main_error = e
            else:
                created_set = script.articleset
                created_n = len(created_articles)
                
            scraper_errors = list(script.get_errors())

            form = script.get_empty_form(project=project)


    return render(request, "navigator/project/upload_action.html", locals())


@check(ArticleSet, args='id', action='delete')
@check(Project, args_map={'projectid' : 'id'}, args='projectid')
def delete_articleset(request, project, aset):
    aset.project = Project.objects.get(id=LITTER_PROJECT_ID)
    aset.indexed = False
    aset.provenance = json.dumps({
        "provenance" : aset.provenance,
        "project" : project.id,
        "deleted_on" : datetime.datetime.now().isoformat()
    })

    aset.save()

    request.session['deleted_articleset'] = True
    return redirect(reverse("project-articlesets", args=[project.id]))

@check(ArticleSet, args='id')
@check(Project, args_map={'projectid' : 'id'}, args='projectid', action='update')
def unlink_articleset(request, project, aset):
    project.articlesets.remove(aset)
    request.session['unlinked_articleset'] = True
    return redirect(reverse("project-articlesets", args=[project.id]))

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


@check(Project)
def import_codebooks(request, project):
    """
    Import a codebook in current project
    """
    # Get codebook form
    data = request.POST if 'submit-codebooks' in request.POST.keys() else None
    codebook_form = forms.ImportCodebook(request.user, data)

    # Get codingschema form
    data = request.POST if 'submit-schemas' in request.POST.keys() else None
    codingschema_form = forms.ImportCodingSchema(request.user, data)

    # Process codebook form
    if codebook_form.is_valid():
        cdbooks = Codebook.objects.filter(id__in=request.POST.getlist('codebooks'))
        for codebook in cdbooks:
            project.codebooks.add(codebook)
        project.save()

    # Process codingschema form
    if codingschema_form.is_valid():
        schemas = CodingSchema.objects.filter(id__in=request.POST.getlist('schemas'))
        for schema in schemas:
            project.codingschemas.add(schema)
        project.save()

    ctx = {
        'menu' : PROJECT_MENU,
        'codebook_form' : codebook_form,
        'codingschema_form' : codingschema_form,
        'context' : project,
    }

    return render(request, "navigator/project/import-codebooks.html", ctx)

### PROJECT MANAGEMENT ###
@check_perm("create_project")
def add(request):
    """
    Render form to add a project. When the project was succesfully created, it
    redirects to its overview page.
    """
    h = ActionHandler(AddProject, user=request.user)
    if h.handle(request):
        return redirect(reverse('project', args=[h.result.id]))
    else:
        return render(request, "navigator/project/add.html", dict(form=h.form, title='project'))

@check(Project, action='update')
def edit(request, project):
    """
    Show / process project edit form
    """
    form = forms.ProjectForm(request.POST or None, instance=project)

    if form.is_valid() and form.save():
        request.session['project-edited'] = True
        return redirect(reverse('project', args=[project.id]))

    return render(request, 'navigator/project/edit.html', locals())

@check_perm("manage_project_users", True)
def users_add(request, id):
    """
    Add (multiple) users.
    """
    project = Project.objects.get(id=id)
    role = Role.objects.get(id=request.POST['role'], projectlevel=True)

    for user in User.objects.filter(id__in=request.REQUEST.getlist('user')):
        ProjectRole(project=project, user=user, role=role).save()

    return redirect(reverse(users_view, args=[project.id]))


@check(ProjectRole, action='update', args=('project', 'user'))
def project_role(request, prole):
    """
    Edit a users role on a project.
    """
    form = forms.ProjectRoleForm(prole.project, prole.user, instance=prole)

    if request.method == 'POST':
        prole.role = Role.objects.get(id=request.POST['role'], projectlevel=True)
        prole.save()

        return redirect(reverse(users_view, args=[prole.project.id]))

    return render(request, "navigator/project/projectrole.html", {'projectrole' : prole,
                                                                   'form' : form})


### CODING JOBS ###
@check(Project, args_map={'project' : 'id'}, args='project')
@check(CodingJob, args_map={'codingjob' : 'id'}, args='codingjob')
def view_codingjob(request, codingjob, project):
    """
    View and edit a codingjob
    """
    form = forms.CodingJobForm(data=(request.POST or None), instance=codingjob)
    articles = Datatable(ArticleMetaResource)\
                    .filter(articleset=codingjob.articleset.id)\
                    .hide("section", "pagenr", "byline", "metastring", "url")\
                    .hide("project", "medium", "text", "uuid")

    if form.is_valid() and form.save():
        return redirect(reverse(codingjobs, args=[project.id]))

    ctx = locals()
    ctx.update(dict(menu=PROJECT_MENU, context=project))

    return render(request, 'navigator/project/edit_codingjob.html', ctx)

@check(Project, args_map={'project' : 'id'}, args='project', action='delete')
@check(CodingJob, args_map={'codingjob' : 'id'}, args='codingjob')
def delete_codingjob(request, codingjob, project):
    codingjob.project_id = LITTER_PROJECT_ID
    codingjob.coder_id = LITTER_USER_ID
    codingjob.save()

    request.session['deleted_codingjob'] = True
    return redirect(reverse("project-codingjobs", args=[project.id]))

from amcat.scripts.actions.add_codingjob import AddCodingJob
from amcat.forms.widgets import convert_to_jquery_select

@check_perm("manage_codingjobs", True)
@check(Project)
def add_codingjob(request, project):
    form = AddCodingJob.options_form(data=request.POST or None, project=project, initial=dict(insertuser=request.user))
    convert_to_jquery_select(form)
    form.fields["insertuser"].widget = forms.HiddenInput()
    if form.is_valid():
        result = AddCodingJob.run_script(form)
        if isinstance(result, CodingJob): result = [result]
        request.session['added_codingjob'] = [job.id for job in result]
        return redirect(reverse("project-codingjobs", args=[project.id]))
        
    ctx = locals()
    ctx['menu'] = PROJECT_MENU
    ctx['title'] = 'codingjob'
    ctx['context'] = project
    return render(request, 'navigator/project/add.html', ctx)
    
