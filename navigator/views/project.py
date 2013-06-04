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
import collections
import itertools
import datetime
import functools

from django.db.models import Q

from api.rest.resources import  ProjectResource, CodebookResource, ArticleMetaResource, AnalysedArticleResource
from api.rest.resources import CodingSchemaResource, ArticleSetResource, CodingJobResource
from api.rest.resources import ProjectRoleResource

#from api.rest import AnalysisResource
from api.rest.resources import CodebookBaseResource, CodebookCodeResource
from api.rest.resources import CodingSchemaFieldResource
from api.rest.resources import PluginResource, ScraperResource

from settings.menu import PROJECT_MENU

from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied

from api.rest.datatable import Datatable, FavouriteDatatable
from api.rest.count import count

from django.template.loader import get_template
from django.template import Context
from django.forms.models import modelform_factory
from django.forms import Form, FileField, ChoiceField
from django.http import HttpResponse
from django.db import transaction
from django.utils.datastructures import SortedDict
from django.utils.functional import SimpleLazyObject
    
from amcat.models import Project, Language, Role, ProjectRole, Code, Label, Article
from amcat.models import CodingJob, Codebook, CodebookCode, CodingSchema
from amcat.models import CodingSchemaField, ArticleSet, Plugin

from amcat.scripts.actions.add_project import AddProject
from amcat.scripts.actions.split_articles import SplitArticles
from amcat.scripts.article_upload.upload import UploadScript
from amcat.scripts.actions.get_codingjob_results import CodingjobListForm, EXPORT_FORMATS
from amcat.scripts.actions.assign_for_parsing import AssignParsing

from navigator import forms
from navigator.utils.auth import check, check_perm
from navigator.utils.action import ActionHandler
from navigator.utils.misc import session_pop

from api.webscripts import mainScripts
from amcat.scripts.forms import SelectionForm
from amcat.scripts.actions.get_codingjob_results import GetCodingJobResults
from amcat.scripts.output.csv_output import TableToSemicolonCSV

from amcat.models.project import LITTER_PROJECT_ID
from amcat.models.user import User
from amcat.models.articleset import create_new_articleset

from api.rest.resources.codebook import CodebookHierarchyResource


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
from navigator.views.article import view as article

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

    can_create_plugin = Plugin.can_create(request.user)

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
            created_articles = script.run()
            created_set = script.articleset
            created_n = len(created_articles)
            form = script.get_empty_form(project=project)


    return render(request, "navigator/project/upload_action.html", locals())

def projectlist(request, what):

        
    if what is None: what = "favourite"
    if what.startswith("/"): what = what[1:]

    tables = [("favourite", "Favourite Projects", dict(active=True)),
              ("my", "My Projects", dict(projectrole__user=request.user, active=True)),
              ("all", "All Projects", dict()),
              ]
    selected_filter = {name : filter for (name, label, filter) in tables}[what]

    # ugly code! but the menu render code will change anyway I suppose...?
    menu = [(label, "projects", {"APPEND":"/"+name}) for (name, label, filter) in tables]
    selected =  {name : label for (name, label, filter) in tables}[what]
    
    if what == "favourite":
        # ugly solution - get project ids that are favourite and use that to filter, otherwise would have to add many to many to api?
        # (or use api request.user to add only current user's favourite status). But good enough for now...
        
        ids = request.user.get_profile().favourite_projects.all().values_list("id")
        ids = [id for (id, ) in ids]
        if ids: 
            selected_filter["pk"] = ids
        else:
            selected_filter["name"] = "This is a really stupid way to force an empty table (so sue me!)"

    url = reverse('project', args=[123]) + "?star="
    table = FavouriteDatatable(set_url=url+"1", unset_url=url+"0", label="project", resource=ProjectResource)
    table = table.filter(**selected_filter)
    table = table.hide("project", "index_dirty", "indexed")

    return render(request, 'navigator/project/projectlist.html', locals())


### VIEW SINGLE PROJECT ###
@check(Project)
def view(request, project):
    """
    View a single project
    """
    edited = session_pop(request.session, "project-edited", False)

    starred = request.user.get_profile().favourite_projects.filter(pk=project.id).exists()
    star = request.GET.get("star")
    if (star is not None):
        if bool(int(star)) != starred:
            starred = not starred
            if starred:
                request.user.get_profile().favourite_projects.add(project.id)
            else:
                request.user.get_profile().favourite_projects.remove(project.id)
    
    return render(request, 'navigator/project/view.html', {
        "context" : project, "menu" : PROJECT_MENU,
        "selected" : "overview", "edited" : edited, "starred" : starred
    })
        

@check(Project)
def articlesets(request, project, what):
    """
    Project articlesets page
    """
    if what is None: what = "favourite"
    if what.startswith("/"): what = what[1:]
    

    tables = [("favourite", '<i class="icon-star"></i> <b>Favourites</b>', dict()),
              ("own", "Own Sets", dict(project=project, codingjob_set__id='null')),
              ("linked", "Linked Sets", dict(projects_set=project)),
              ("codingjob", "Coding Job Sets", dict()),
              ]
    selected_filter = {name : filter for (name, label, filter) in tables}[what]

    if what == "favourite":
        # ugly solution - get project ids that are favourite and use that to filter, otherwise would have to add many to many to api?
        # (or use api request.user to add only current user's favourite status). But good enough for now...
        
        ids = request.user.get_profile().favourite_articlesets.filter(Q(project=project.id) | Q(projects_set=project.id))
        ids = [id for (id, ) in ids.values_list("id")]
        if ids: 
            selected_filter["pk"] = ids
        else:
            selected_filter["name"] = "This is a really stupid way to force an empty table (so sue me!)"
            
    elif what == "codingjob":
        # more ugliness. Filtering the api on codingjob_set__id__isnull=False gives error from filter set
        ids = ArticleSet.objects.filter(Q(project=project.id) | Q(projects_set=project.id), codingjob_set__id__isnull=False)
        ids = [id for (id, ) in ids.values_list("id")]
        if ids: 
            selected_filter["pk"] = ids
        else:
            selected_filter["name"] = "This is a really stupid way to force an empty table (so sue me!)"
    
    url = reverse('articleset', args=[project.id, 123]) 
    
    table =  FavouriteDatatable(resource=ArticleSetResource, rowlink=url.replace("123", "{id}"),
                                label="article set", set_url=url + "?star=1", unset_url=url+"?star=0")
    table = table.filter(**selected_filter)
    table = table.hide("project", "index_dirty", "indexed")

    context = project
    menu = PROJECT_MENU
    deleted = session_pop(request.session, "deleted_articleset")
    unlinked = session_pop(request.session, "unlinked_articleset")
    selected = "article sets"
    
    return render(request, 'navigator/project/articlesets.html', locals())

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

@check(ArticleSet, args='id')
@check(Project, args_map={'projectid' : 'id'}, args='projectid', action='update')
def refresh_articleset(request, project, aset):
    aset.reset_index(full_refresh=True)
    return redirect(reverse("articleset", args=[project.id, aset.id]))


@check(ArticleSet, args='id', action='update')
@check(Project, args_map={'projectid' : 'id'}, args='projectid')
def edit_articleset(request, project, aset):
    form = modelform_factory(ArticleSet, fields=("project", "name", "provenance"))
    form = form(instance=aset, data=request.POST or None)
        
    form.fields['project'].queryset = Project.objects.filter(projectrole__user=request.user,
                                                             projectrole__role_id__gte=PROJECT_READ_WRITE)
    
    if form.is_valid():
        form.save()

    return render(request, 'navigator/project/edit_articleset.html', {
        "context" : project, "menu" : PROJECT_MENU, "selected" : "overview",
        "form" : form, "articleset" : aset, 
    })


@check(ArticleSet, args='id')
@check(Project, args_map={'projectid' : 'id'}, args='projectid')
def articleset(request, project, aset):
    cls = "Article Set"
    articles = (Datatable(ArticleMetaResource, rowlink='../article/{id}')
                .filter(articlesets_set__id=aset.id)
                .hide('metastring', 'url', 'externalid',
                      'byline', 'pagenr', 'project', 'section', 'text'))



    profile = request.user.get_profile()
    starred = profile.favourite_articlesets.filter(pk=aset.id).exists()
    star = request.GET.get("star")
    if (star is not None):
        if bool(int(star)) != starred:
            starred = not starred
            if starred:
                profile.favourite_articlesets.add(aset.id)
            else:
                profile.favourite_articlesets.remove(aset.id)

    
    indexed = request.GET.get("indexed")
    if indexed is not None:
        indexed = bool(int(indexed))
        if indexed != aset.indexed:
            aset.indexed = indexed
            aset.index_dirty = True
            aset.save()
    
    can_update = aset.can_update(request.user)
    if can_update:
        form = forms.ArticleSetForm(request.POST or None, instance=aset)
        if form.is_valid():
            form.save()
        else:
            pass
    
    return table_view(request, project, articles, form=form, object=aset, cls=cls, starred=starred,
                      template="navigator/project/articleset.html", articlecount=count(aset.articles.all()))



@check(Project)
def selection(request, project):
    """
    Render article selection page.

    TODO:
     - update to meet PEP8 style
     - remove/replace webscripts (?)
    """
    outputs = []
    for ws in mainScripts:
        outputs.append({
            'id':ws.__name__, 'name':ws.name,
            'formAsHtml': ws.formHtml(project)
        })

    formData = request.GET.copy()
    formData['projects'] = project.id

    all_articlesets = project.all_articlesets()

    favourites = json.dumps(tuple(request.user.userprofile.favourite_articlesets.all().values_list("id", flat=True)))
    indexed = json.dumps(tuple(all_articlesets.filter(indexed=True, index_dirty=False).values_list("id", flat=True)))
    indexed_with_dirty = json.dumps(tuple(all_articlesets.filter(indexed=True).values_list("id", flat=True)))
    codingjobs = json.dumps(tuple(CodingJob.objects.filter(articleset__in=all_articlesets).values_list("articleset_id", flat=True)))
    all_sets = json.dumps(tuple(all_articlesets.values_list("id", flat=True)))

    ctx = locals()
    ctx.update({
        'form' : SelectionForm(formData, initial={"datetype" : "all" }),
        'outputs' : outputs,
        'project' : project,
        'context' : project,
        'menu' : PROJECT_MENU,
        'selected' : 'query'
    })

    return render(request, 'navigator/project/selection.html', ctx)

@check(Project)
def codingjobs(request, project):
    """
    Coding-jobs tab
    """
    cdjobs = (Datatable(CodingJobResource, rowlink='./codingjob/{id}')
                .filter(project=project).hide('project').order_by("-insertdate"))

    return table_view(request, project, cdjobs, 'codingjobs',
           template="navigator/project/codingjobs.html")

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
            response = HttpResponse(content_type=eformat.mimetype, status=201)
            response['Content-Disposition'] = 'attachment; filename="{filename}"'.format(**locals())
            response.write(results)
            return response

    return render(request, 'navigator/project/export_options.html', locals())

@check(Project)
def schemas(request, project):
    """
    Codingschemas-tab
    """
    owned_schemas = Datatable(CodingSchemaResource, rowlink='./schema/{id}').filter(project=project)
    linked_schemas = (Datatable(CodingSchemaResource, rowlink='./schema/{id}').
                      filter(projects_set=project))

    ctx = {
        'owned_schemas' : owned_schemas,
        'linked_schemas' : linked_schemas,
        'menu' : PROJECT_MENU,
        'selected' : 'codingschemas',
        'context' : project
    }

    return render(request, "navigator/project/schemas.html", ctx)


@check(Project, args_map={'project' : 'id'}, args='project')
@check(CodingSchema, args_map={'schema' : 'id'}, args='schema')
def schema(request, schema, project):
    fields = (Datatable(CodingSchemaFieldResource)
              .filter(codingschema=schema).hide('id', 'codingschema'))

    return table_view(request, project, fields, 'codingschemas',
            template="navigator/project/schema.html", schema=schema,
            is_new=session_pop(request.session, "schema_{}_is_new".format(schema.id), False),
            is_edited=session_pop(request.session, "schema_{}_edited".format(schema.id), False))

@check(Project, args_map={'project' : 'id'}, args='project')
def new_schema(request, project):
    schema = CodingSchema.objects.create(name="Untitled schema", project=project)
    return redirect(reverse("project-edit-schema", args=(project.id, schema.id)))

@check(Project, args_map={'project' : 'id'}, args='project')
@check(CodingSchema, args_map={'schema' : 'id'}, args='schema')
def edit_schema(request, schema, project):
    if request.method == "POST" and not "codingschema-submit" in request.POST:
        return _edit_schemafields_post(request, schema, project)

    # Is this schema imported?
    if schema.project != project:
        # Offer to copy it to currect project
        return redirect(copy_schema, project.id, schema.id)

    fields_null = dict([(f.name, f.null) for f in CodingSchemaField._meta.fields])
    form = forms.CodingSchemaForm(data=request.POST or None, instance=schema, hidden="project")

    if request.method == "POST" and "codingschema-submit" in request.POST:
        # Process codingschema form
        if form.is_valid():
            form.save()

            request.session["schema_{}_edited".format(schema.id)] = True 
            return redirect(reverse("project-schema", args=(project.id, schema.id)))

    # This schema is owned by current project. Offer edit interface.
    return table_view(request, project, None, 'codingschemas',
            template="navigator/project/edit_schema.html",
            schema=schema, fields_null=fields_null, schema_form=form)

def _get_schemafield_forms(fields, schema):
    for field in fields:
        # Check wether field already exists
        id = field.get('id')
        field['codingschema'] = schema.id
        
        instance = CodingSchemaField.objects.get(id=id) if id else None
        yield forms.CodingSchemaFieldForm(data=field, instance=instance)

def _get_form_errors(forms):
    """
    Check each form for errors. If an error is found in a form, a tuple
    of the form:

      (fieldnr, errors_dict)

    is yielded.
    """
    return ((f.data['fieldnr'], f.errors) for f in forms if not f.is_valid())

def _edit_schemafields_post(request, schema, project, commit=None):
    """
    View executed when making a POST request to edit_schema.
    """
    commit = request.GET.get("commit", commit) in (True, "true")
    fields = json.loads(request.POST['fields'])

    forms = list(_get_schemafield_forms(fields, schema))
    errors = dict(_get_form_errors(forms))

    if not errors and commit:
        fields = [form.save(commit=False) for form in forms]

        for i, field in enumerate(fields):
            field.fieldnr = (i+1) * 10
            field.save()

        for field in set(schema.fields.all()) - set(fields):
            # Remove deleted fields
            field.delete()

        request.session["schema_{}_edited".format(schema.id)] = True 

    # Always send response (don't throw an error)
    schema_url = reverse("project-schema", args=[project.id, schema.id])

    return HttpResponse(
        json.dumps(dict(fields=errors, schema_url=schema_url)),
        mimetype='application/json'
    )

@check(Project, args_map={'project' : 'id'}, args='project')
@check(CodingSchema, args_map={'schema' : 'id'}, args='schema')
@check(CodingSchemaField, args_map={'schemafield' : 'id'}, args='schemafield', action='update')
def edit_schemafield(request, schemafield, schema, project):
    # Require url to be correct
    assert(schema.project == project)
    assert(schemafield.codingschema == schema)

    schemaform = forms.CodingSchemaFieldForm(request.POST or None, instance=schemafield)

    if request.POST and schemaform.is_valid():
        for field, val in schemaform.cleaned_data.items():
            setattr(schemafield, field, val)

        schemafield.save()
        return redirect(edit_schema, project.id, schema.id)

    return table_view(request, project, None, 'codingschemas',
            template="navigator/project/edit_schemafield.html",
            schemaform=schemaform, schema=schema, schemafield=schemafield)
    

@check(Project, args_map={'project' : 'id'}, args='project')
@check(CodingSchema, args_map={'schema' : 'id'}, args='schema')
@check(CodingSchemaField, args_map={'schemafield' : 'id'}, args='schemafield', action='delete')
def delete_schemafield(request, schemafield, schema, project):
    assert(schema.project == project)
    assert(schemafield.codingschema == schema)

    if request.POST:
        if (request.POST.get("yes", "no").lower() == "yes"):
            # Yes clicked
            schemafield.delete()
            return redirect(edit_schema, project.id, schema.id)

        return redirect(edit_schemafield, project.id, schema.id, schemafield.id)

    return table_view(request, project, None, 'codingschemas',
            template="navigator/project/delete_schemafield.html",
            schema=schema, schemafield=schemafield)

@check(Project, args_map={'project' : 'id'}, args='project')
@check(CodingSchema, args_map={'schema' : 'id'}, args='schema')
def copy_schema(request, schema, project):
    """
    Offer a user to copy a schema to his project
    """
    if request.POST:
        do_copy = (request.POST.get("yes", "no").lower() == "yes")

        if do_copy:
            return redirect(name_schema, project.id, schema.id)

        return redirect("project-schema", project.id, schema.id)

    return table_view(request, project, None, 'codingschemas',
            template="navigator/project/copy_schema.html")

@check(Project, args_map={'project' : 'id'}, args='project')
@check(CodingSchema, args_map={'schema' : 'id'}, args='schema')
def name_schema(request, schema, project):
    """
    User confirmed copying schema, ask for a name to give.
    """
    if request.POST:
        if 'cancel' in request.POST:
            return redirect("project-schema", project.id, schema.id)
        
        # No, copy as requested
        new_schema = CodingSchema(
            name=request.POST.get("name"), description=schema.description,
            isnet=schema.isnet, isarticleschema=schema.isarticleschema,
            quasisentences=schema.quasisentences, project=project
        )

        new_schema.save()

        for field in schema.fields.all():
            field.id = None
            field.codingschema = new_schema
            field.save()

        request.session["schema_%s_is_new" % new_schema.id] = True
        return redirect("project-schema", project.id, new_schema.id)

    return table_view(request, project, None, 'codingschemas',
            template="navigator/project/name_schema.html",
            schema=schema)


@check(Project)
def add_codebook(request, project):
    """
    Add codebook automatically creates an empty codebook and opens the edit codebook page
    """
    c = Codebook.objects.create(project=project, name='New codebook')
    return redirect(reverse('project-codebook', args=[project.id, c.id]))

@check(Project)
def codebooks(request, project):
    """
    Codebooks-tab.
    """
    owned_codebooks = Datatable(CodebookResource, rowlink='./codebook/{id}').filter(project=project)
    linked_codebooks = (Datatable(CodebookResource, rowlink='./codebook/{id}')
                        .filter(projects_set=project))

    can_import = project.can_update(request.user)
    can_create = Codebook.can_create(request.user) and project.can_update(request.user)

    context = project
    menu = PROJECT_MENU
    selected = "codebooks"
    return render(request, "navigator/project/codebooks.html", locals())


@check(Project)
def preprocessing(request, project):
    """
    Codebooks-tab.
    """
    table = Datatable(AnalysedArticleResource).filter(article__articlesets_set__project=project)

    form = AssignParsing.options_form(request.POST or None)
    form.fields['articleset'].queryset = ArticleSet.objects.filter(pk__in=project.all_articlesets())

    if form.is_valid():
        assigned_n = AssignParsing(form).run()
        assigned_plugin = form.cleaned_data["plugin"]
        assigned_set = form.cleaned_data["articleset"]


    context = project
    menu = PROJECT_MENU
    selected = "preprocessing"
    return render(request, "navigator/project/preprocessing.html", locals())


@check(Project, args_map={'project' : 'id'}, args='project')
@check(Codebook, args_map={'codebook' : 'id'}, args='codebook')
def codebook(request, codebook, project):
    return table_view(request, project, None, 'codebooks',
            template="navigator/project/codebook.html", codebook=codebook)

def _get_new_labels(labels, code):
    for lbl in labels:
        yield Label(
            language=Language.objects.get(id=lbl.language),
            code=code, label=lbl["label"]
        )

@check(Project, args_map={'project' : 'id'}, args='project')
@check(Codebook, args_map={'codebook' : 'id'}, args='codebook', action="update")
def save_name(request, codebook, project):
    codebook.name = request.POST.get("codebook_name")
    codebook.save()

    return HttpResponse(status=200)

def _save_moves(request, codebook, moves):
    """
    Helper function for save_changesets
    """
    move_codes_ids = set(itertools.chain(*[tuple(m.values()) for m in moves]))
    move_codes = { c.id : c for c in Code.objects.filter(id__in=move_codes_ids)}
    move_codebook_codes = { 
        c.code.id : c for c in CodebookCode.objects.filter(
            codebook=codebook, code__in=move_codes
        ).select_related("code__id")
    }

    # Account for bad user input
    if len(move_codes_ids) != len(move_codes):
        return HttpResponse(status=400, content="Non-existing code requested")


def _get_codebook_code(ccodes, code, codebook):
    """
    Get CodebookCode object from dictionary of (cached) codebookcodes. If not
    available, create a new one and add it to the dict.
    """
    if code.id not in ccodes:
        ccodes[code.id] = CodebookCode.objects.create(code=code, codebook=codebook)

    return ccodes.get(code.id)

@transaction.commit_on_success
@check(Project, args_map={'project' : 'id'}, args='project')
@check(Codebook, args_map={'codebook' : 'id'}, args='codebook', action="update")
def save_changesets(request, codebook, project):
    moves = json.loads(request.POST.get("moves", "[]"))
    hides = json.loads(request.POST.get("hides", "[]"))

    # Gather all codes needed for moves and hides (so that we don't have to
    # retrieve them on by one
    codes = { c.id : c for c in Code.objects.filter(id__in=itertools.chain(
        set([h["code_id"] for h in hides]),
        set(itertools.chain.from_iterable(m.values() for m in moves))
    )) }

    codebook_codes = { 
        c.code.id : c for c in CodebookCode.objects.filter(
            codebook=codebook, code__in=codes
        ).select_related("code__id")
    }

    # Save all moves
    for move in moves:
        code, new_parent = codes[move['code_id']], codes.get(move['new_parent'])
        ccode = _get_codebook_code(codebook_codes, code, codebook)

        # User must have sufficient privileges to read both codes and update the codebookcode 
        if new_parent is not None:
            if not new_parent.can_read(request.user):
                raise PermissionDenied

        if not (code.can_read(request.user) and ccode.can_update(request.user)):
            raise PermissionDenied()

        ccode.parent = new_parent

    # Save all hides
    for hide in hides:
        ccode = _get_codebook_code(codebook_codes, codes[hide['code_id']], codebook)
        ccode.hide = hide.get("hide", False)

    # Commit all changes
    for ccode_id, ccode in codebook_codes.items():
        ccode.save()

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
        # New code should be created
        if not Code.can_create(request.user):
            raise PermissionDenied

        code = Code.objects.create()
        parent = json.loads(request.POST["parent"])

        CodebookCode.objects.create(
            parent=None if parent is None else Code.objects.get(id=parent),
            code=code, codebook=codebook
        )

    else:
        code = Code.objects.get(id=int(request.POST['code']))

        if not code.can_update(request.user):
            raise PermissionDenied

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

@check(Project)
def users_view(request, project):
    """
    View all users affiliated with this project. Also render a form
    to add users to the project (if permissions are met).
    """
    users = Datatable(ProjectRoleResource, rowlink='./user/{user_id}')\
            .filter(project=project).hide('project', 'id')

    if request.user.get_profile().haspriv('manage_project_users', project):
        add_user = forms.ProjectRoleForm(project)

    ctx = dict(locals())
    ctx.update({
        'menu' : PROJECT_MENU,
        'selected' : 'users',
        'context' : project
    })

    return render(request, 'navigator/project/users.html', ctx)

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
                    .filter(articlesets_set=codingjob.articleset)\
                    .hide("section", "pagenr", "byline", "metastring", "url")\
                    .hide("project", "medium", "text", "uuid")

    if form.is_valid() and form.save():
        return redirect(reverse(codingjobs, args=[project.id]))

    ctx = locals()
    ctx.update(dict(menu=PROJECT_MENU, context=project))

    return render(request, 'navigator/project/edit_codingjob.html', ctx)

@check_perm("manage_codingjobs", True)
@check(Project)
def add_codingjob(request, project):
    """
    Add codingjob to a project
    """
    form = forms.CodingJobForm(project=project, edit=False, data=request.POST or None)

    form.saved = False
    if form.is_valid():
        # Save form and set flag on form indicating it's saved.
        cj = form.save(commit=False)
        cj.insertuser = request.user
        cj.project = project

        # Copy articleset, as is done in api/webscripts/assign_codingjob.py
        # AssignCodingJob.run()
        a = create_new_articleset(cj.name, project)
        a.add_articles(cj.articleset.articles.all())
        cj.articleset = a
        # Split all articles 
        cj.save()

        SplitArticles(dict(articlesets=[a.id])).run()

        form = forms.CodingJobForm(project=project, edit=False, data=None)
        form.saved = True

    # Create context for template
    ctx = locals()
    ctx['menu'] = PROJECT_MENU
    ctx['title'] = 'codingjob'
    ctx['context'] = project

    return render(request, 'navigator/project/add.html', ctx)
