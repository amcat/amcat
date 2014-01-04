from amcat.models import CodingSchema, authorisation
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from api.rest.datatable import Datatable
from django.views.generic.base import RedirectView
from django.views.generic.edit import CreateView, UpdateView
from api.rest.resources import CodingSchemaResource
from amcat.models.project import LITTER_PROJECT_ID
from django.core.urlresolvers import reverse
from django.forms.widgets import HiddenInput

class CodingSchemaListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, ListView):
    model = CodingSchema
    parent = ProjectDetailsView
    context_category = 'Coding'

    def get_context_data(self, **kwargs):
        ctx = super(CodingSchemaListView, self).get_context_data(**kwargs)
        owned_schemas = Datatable(CodingSchemaResource, rowlink='./{id}').filter(project=self.project)
        linked_schemas = (Datatable(CodingSchemaResource, rowlink='./{id}')
                        .filter(projects_set=self.project))
        
        ctx.update(locals())
        return ctx

class CodingSchemaDetailsView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DetailView):
    model = CodingSchema
    parent = CodingSchemaListView
    context_category = 'Coding'


    
class CodingSchemaDeleteView(ProjectViewMixin, HierarchicalViewMixin, RedirectView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaDetailsView
    url_fragment = "delete"
    model = CodingSchema
    
    def get_redirect_url(self, project_id, codingschema_id):
        schema = self.get_object()
        schema.project_id = LITTER_PROJECT_ID
        schema.save()
        self.request.session['deleted_schema'] = codingschema_id
        
        return reverse("coding schema-list", args=(project_id, ))

class CodingSchemaCreateView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, CreateView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaListView
    url_fragment = "new"
    model = CodingSchema
    
    def get_initial(self):
        initial = super(CodingSchemaCreateView, self).get_initial()
        initial["project"]=self.project
        return initial

        
    def get_form(self, form_class):
        form = super(CodingSchemaCreateView, self).get_form(form_class)
        form.fields["project"].widget = HiddenInput()
        return form

    def get_success_url(self):
        return reverse("coding schema-details", args=(self.project.id, self.object.id))

class CodingSchemaEditView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, UpdateView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaDetailsView
    url_fragment = "edit"
    model = CodingSchema

    def get_success_url(self):
        return reverse("coding schema-details", args=(self.project.id, self.object.id))
