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
import itertools
import json

from django import forms
from django.http import HttpResponse
from django.views.generic.list import ListView
from jsonfield.forms import JSONFormField

from amcat.forms import widgets
from amcat.models import Code, Codebook, CodebookCode, Label, Language, Project, PROJECT_ROLES
from amcat.scripts.actions.export_codebook import ExportCodebook
from amcat.scripts.actions.export_codebook_as_xml import ExportCodebookAsXML
from amcat.scripts.actions.import_codebook import ImportCodebook
from api.rest.datatable import Datatable
from api.rest.resources import CodebookHierarchyResource
from api.rest.viewsets import CodebookViewSet
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import BreadCrumbMixin, HierarchicalViewMixin, ProjectActionRedirectView, \
    ProjectDetailView, ProjectFormView, ProjectScriptView, ProjectViewMixin, ProjectActionForm
from navigator.views.scriptview import TableExportMixin


class CodebookListView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, ListView):
    model = Codebook
    parent = ProjectDetailsView
    context_category = 'Coding'
    view_name = "coding codebook-list"


    def get_context_data(self, **kwargs):
        ctx = super(CodebookListView, self).get_context_data(**kwargs)
        all_codebooks = Datatable(CodebookViewSet, rowlink='./{id}', url_kwargs={"project" : self.project.id}).hide("codes")
        owned_codebooks = all_codebooks.filter(project=self.project).hide("project")
        linked_codebooks = all_codebooks.filter(projects_set=self.project)

        ctx.update(locals())
        return ctx

class CodebookDetailsView(ProjectDetailView):
    parent = CodebookListView
    view_name = "coding codebook-details"




class ExportCodebook(TableExportMixin, ProjectScriptView):
    script = ExportCodebook
    parent = CodebookDetailsView
    url_fragment = "export"

    def export_filename(self, form):
        c = form.cleaned_data["codebook"]
        return "Codebook {c.id} {c}".format(**locals())

    def get_form_class(self):
        # Modify form class to also contain XML output
        form_class = super(ExportCodebook, self).get_form_class()
        form_class.base_fields['format'].choices.append(("xml", "XML"))
        form_class.base_fields['format'].choices.remove(("spss", "SPSS"))
        form_class.base_fields['format'].choices.remove(("html", "HTML"))
        return form_class


    def form_valid(self, form):
        if form.cleaned_data['format'] == 'xml':
            return ExportCodebookXML.as_view()(self.request, **self.kwargs)

        return super(ExportCodebook, self).form_valid(form)

class ExportCodebookXML(ProjectScriptView):
    script = ExportCodebookAsXML
    parent = CodebookDetailsView

    def export_filename(self, form):
        c = form.cleaned_data["codebook"]
        return "Codebook {c.id} {c}.xml".format(**locals())

    def get_initial(self):
        return dict(codebook=self.kwargs["codebook"])

    def form_valid(self, form):
        super(ExportCodebookXML, self).form_valid(form)

        filename = self.export_filename(form)
        response = HttpResponse(self.result, content_type='text/xml', status=200)
        response['Content-Disposition'] = 'attachment; filename="{filename}"'.format(**locals())
        return response

class CodebookImportView(ProjectScriptView):
    required_project_permission = PROJECT_ROLES.WRITER
    script = ImportCodebook
    parent = CodebookListView
    url_fragment = 'import'

    def get_form(self, form_class=None):
        form = super(CodebookImportView, self).get_form(form_class)
        form.fields['codebook'].queryset = self.project.codebook_set.all()
        return form

    def get_initial(self):
        initial = super(CodebookImportView, self).get_initial()
        initial["codebook"] = self.kwargs.get("codebookid")
        return initial

    def post(self, request, *args, **kwargs):
        try:
            return super(CodebookImportView, self).post(request, *args, **kwargs)

        except UnicodeDecodeError:
            form = self.get_form(ImportCodebook.options_form)
            form.errors["encoding"] = ["Could not decode the file using UTF-8"]
            return self.form_invalid(form)

        except (ValueError, IndexError):
            form = self.get_form(ImportCodebook.options_form)
            form.errors["file"] = ["Couldn't parse the file as CSV using the given dialect"]
            form.errors["dialect"] = form.errors["file"]
            return self.form_invalid(form)

class CodebookAddView(ProjectActionRedirectView):
    """
    Add codebook automatically creates an empty codebook and opens the edit codebook page
    """
    parent = CodebookListView
    url_fragment = "add"

    
    def action(self, project):
        self.object = Codebook.objects.create(project_id=project, name='New codebook')
        
    def get_redirect_url(self, **kwargs):
        kwargs.update({"codebook" : self.object.id})
        return CodebookDetailsView._get_breadcrumb_url(kwargs, self)

        

        
class CodebookLinkView(ProjectFormView):
    required_project_permission = PROJECT_ROLES.WRITER
    parent = CodebookListView
    url_fragment = 'link'

    class form_class(forms.Form):
        codebooks = forms.MultipleChoiceField(widget=widgets.BootstrapMultipleSelect)

    def get_form(self, form_class=None):
        form = super(CodebookLinkView, self).get_form(form_class)
        from navigator.forms import gen_coding_choices
        form.fields['codebooks'].choices = gen_coding_choices(self.request.user, Codebook)
        return form

    def form_valid(self, form):
        cbs = form.cleaned_data['codebooks']
        for cb in cbs:
            self.project.codebooks.add(cb)
        self.request.session['notification'] = "Linked {n} codebook(s)".format(n=len(cbs))
        return super(CodebookLinkView, self).form_valid(form)

class CodebookUnlinkActionForm(ProjectActionForm):
    pass

class CodebookUnlinkView(ProjectActionRedirectView):
    parent = CodebookDetailsView
    url_fragment = "unlink"

    def action(self, project, codebook):
        cb = Codebook.objects.get(pk=codebook)
        project = Project.objects.get(pk=project)
        project.codebooks.remove(cb)

    def get_redirect_url(self, **kwargs):
        return CodebookListView._get_breadcrumb_url(kwargs, self)
        

class CodebookDeleteView(ProjectActionRedirectView):
    parent = CodebookDetailsView
    url_fragment = "delete"

    def get_redirect_url(self, **kwargs):
        return CodebookListView._get_breadcrumb_url(kwargs, self)

    def action(self, project, codebook):
        cb = Codebook.objects.get(pk=codebook)
        cb.recycle()

class CodebookFormActionView(ProjectFormView):
    """Base class for simple form based actions on codebooks"""
    required_project_permission = PROJECT_ROLES.WRITER
    parent = CodebookDetailsView
    def form_invalid(self, form):
        error = {
            'success': False,
            'errors': dict(form.errors.items()),
        }
        
        return HttpResponse(json.dumps(error, indent=2),
                            content_type='application/json; charset=UTF-8',
                            status=500)
        
    def form_valid(self, form):
        codebook = Codebook.objects.get(pk=self.kwargs["codebook"])
        result = self.action(codebook, form)
        return HttpResponse(content=result, status=200)
    def action(self, codebook, form):
        """Perform the action. An optional return value will become the HttpResponse 201 content"""
        raise NotImplementedError()
    
class CodebookChangeNameView(CodebookFormActionView):
    url_fragment = "change-name"
    class form_class(forms.Form):
        codebook_name = forms.CharField()
    def action(self, codebook, form):
        codebook.name = form.cleaned_data["codebook_name"]
        codebook.save()


class CodebookSaveChangesetsView(CodebookFormActionView):
    url_fragment = "save-changesets"
    class form_class(forms.Form):
        moves = JSONFormField(required=False)
        hides = JSONFormField(required=False)
        reorders = JSONFormField(required=False)

    def action(self, codebook, form):
        moves, hides, reorders = [form.cleaned_data.get(x, []) for x in ["moves", "hides", "reorders"]]
        
        codebook.cache()

        # Keep a list of changed codebookcodes
        changed_codes = [x["code_id"] for x in itertools.chain(hides, reorders, moves)]

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
        CodebookHierarchyResource.get_tree(Codebook.objects.get(id=codebook.id))

class CodebookAddCodeView(CodebookFormActionView):
    """
    View called by code-editor to create new code
    """
    
    url_fragment = "new-code"
    class form_class(forms.Form):
        parent = JSONFormField(required=False)
        label = forms.CharField()
        ordernr = JSONFormField(required=False)

    def action(self, codebook, form):
        label = form.cleaned_data["label"]
        parent = form.cleaned_data["parent"]
        ordernr = form.cleaned_data["ordernr"]
        
        code = Code.objects.create(label=label)
        CodebookCode.objects.create(parent_id=parent, code=code, ordernr=ordernr, codebook=codebook)
        
        content = json.dumps(dict(code_id=code.id))
        return HttpResponse(content=content, status=201, content_type="application/json")
        
class CodebookSaveLabelsView(CodebookFormActionView):
    """
    View called by code-editor to store new labels. It requests
    two values in POST:

     - labels: an (json-encoded) list with label-objects
     - code: an (json-encoded) code object to which the labels belong
    """
    url_fragment = "save-labels"
    class form_class(forms.Form):
        code = JSONFormField()
        label = forms.CharField()
        labels = JSONFormField(required=False)
        parent = JSONFormField(required=False)

    def action(self, codebook, form):
        code = Code.objects.get(id=form.cleaned_data["code"])
        label = form.cleaned_data["label"]
        labels = form.cleaned_data["labels"]

        if label:
            code.label = label
            code.save()
            
        if labels:
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

