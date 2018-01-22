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
from django.core.exceptions import ValidationError
from django.shortcuts import redirect

from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django import forms
import itertools
from amcat.forms import widgets
from amcat.forms.fields import StaticModelChoiceField
from amcat.forms.widgets import convert_to_bootstrap_select

from amcat.models import CodingSchema, authorisation, CodingSchemaField, CodingSchemaFieldType, CodingRule, Code, \
    Project, PROJECT_ROLES
from amcat.models.coding.serialiser import CodebookSerialiser, BooleanSerialiser
from api.rest.viewsets import _CodingSchemaFieldViewSet, CodingSchemaViewSet
from navigator.forms import CodingSchemaForm
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectFormView, ProjectActionRedirectView
from navigator.views.datatableview import DatatableMixin
from api.rest.datatable import Datatable
from amcat.models.project import LITTER_PROJECT_ID
from amcat.models.coding import codingruletoolkit
from navigator.utils.misc import session_pop


class CodingSchemaListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, ListView):
    model = CodingSchema
    parent = ProjectDetailsView
    context_category = 'Coding'

    def get_context_data(self, **kwargs):
        ctx = super(CodingSchemaListView, self).get_context_data(**kwargs)
        schemas = Datatable(CodingSchemaViewSet, rowlink="./{id}", url_kwargs=dict(project=self.project.id)).hide("highlighters")
        owned_schemas = schemas.filter(project=self.project)
        linked_schemas = schemas.filter(projects_set=self.project)
        ctx.update(locals())
        return ctx



class CodingSchemaDetailsView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, DetailView):
    model = CodingSchema
    parent = CodingSchemaListView
    context_category = 'Coding'
    resource = _CodingSchemaFieldViewSet

    def get_context_data(self, **kwargs):
        ctx = super(CodingSchemaDetailsView, self).get_context_data(**kwargs)
        object = self.get_object()
        is_new=session_pop(self.request.session, "schema_{}_is_new".format(object.id), False)
        is_edited=session_pop(self.request.session, "schema_{}_edited".format(object.id), False)
        ctx.update(locals())
        return ctx

    def get_datatable(self, **kwargs):
        return super(CodingSchemaDetailsView, self).get_datatable(
            url_kwargs=dict(project=self.project.id, codingschema=self.object.id)
        )

    def filter_table(self, table):
        return table.hide("codingschema")

class CodingSchemaNameView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, TemplateView):
    model = CodingSchema
    parent = CodingSchemaDetailsView
    context_category = 'Coding'
    url_fragment = "name"

    @classmethod
    def get_view_name(cls):
        return "codingschema-name"

    def post(self, *args, **kwargs):
        schema = self.get_object()

        if 'cancel' in self.request.POST:
            return redirect("navigator:codingschema-details", self.project.id, schema.id)

        # No, copy as requested
        new_schema = CodingSchema(
            name=self.request.POST.get("name"), description=schema.description,
            isarticleschema=schema.isarticleschema, subsentences=schema.subsentences,
            highlight_language=schema.highlight_language,
            project=self.project
        )

        new_schema.save()

        for field in schema.fields.all():
            field.id = None
            field.codingschema = new_schema
            field.save()

        self.request.session["notification"] = ("Copied codingschema. "
                                                "You can return to the overview using the 'Coding Schemas' link above")
        return redirect("navigator:codingschema-details", self.project.id, new_schema.id)


class CodingSchemaCopyView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, TemplateView):
    model = CodingSchema
    parent = CodingSchemaDetailsView
    context_category = 'Coding'
    url_fragment = "copy"

    @classmethod
    def get_view_name(cls):
        return "codingschema-copy"

    def post(self, *args, **kwargs):
        do_copy = (self.request.POST.get("yes", "no").lower() == "yes")
        redirect_class = CodingSchemaNameView if do_copy else CodingSchemaDetailsView
        return redirect(redirect_class, self.project.id, self.get_object().id)

class CodingSchemaDeleteView(ProjectViewMixin, HierarchicalViewMixin, RedirectView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaDetailsView
    url_fragment = "delete"
    model = CodingSchema
    
    def get_redirect_url(self, project, codingschema):
        schema = self.get_object()
        schema.project_id = LITTER_PROJECT_ID
        schema.save()
        self.request.session['deleted_schema'] = codingschema
        
        return reverse("navigator:codingschema-list", args=(project, ))

class CodingSchemaCreateView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, CreateView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaListView
    url_fragment = "new"
    model = CodingSchema
    form_class = CodingSchemaForm


    def get_form(self, form_class=None):
        form = super(CodingSchemaCreateView, self).get_form(form_class)
        form.fields["project"] = StaticModelChoiceField(self.project)
        form.fields["highlighters"].required = False
        convert_to_bootstrap_select(form)
        return form

    def get_success_url(self):
        return reverse("navigator:codingschema-details", args=(self.project.id, self.object.id))


class CodingSchemaEditView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, UpdateView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaDetailsView
    url_fragment = "edit"
    form_class = CodingSchemaForm

    def get_form(self, form_class=None):
        form = super(CodingSchemaEditView, self).get_form(form_class)
        form.fields["highlighters"].required = False
        return form

    def get_success_url(self):
        return reverse("navigator:codingschema-details", args=(self.project.id, self.object.id))


class CodingSchemaEditFieldsView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, TemplateView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaDetailsView
    url_fragment = "fields"


    def get_context_data(self, **kwargs):
        ctx = super(CodingSchemaEditFieldsView, self).get_context_data(**kwargs)
        fields_null = dict([(f.name, f.null) for f in CodingSchemaField._meta.fields])
        rules_valid=json.dumps(codingruletoolkit.schemarules_valid(self.get_object()))
        ctx.update(locals())
        return ctx
    
    def get(self, *args, **kargs):
        if self.get_object().project != self.project:
            # Offer to copy it to currect project
            pass#return redirect(copy_schema, project.id, schema.id)
        return super(CodingSchemaEditFieldsView, self).get(*args, **kargs)

    def post(self, *args, **kargs):
        commit = self.request.GET.get("commit") in (True, "true")
        fields = json.loads(self.request.POST['fields'])
        schema = self.get_object()

        forms = list(self._get_schemafield_forms(fields))
        errors = dict(_get_form_errors(forms))

        if not errors and commit:
            fields = [form.save(commit=False) for form in forms]

            for i, field in enumerate(fields):
                field.fieldnr = (i+1) * 10
                field.save()

            for field in set(schema.fields.all()) - set(fields):
                # Remove deleted fields
                field.delete()

            self.request.session["schema_{}_edited".format(schema.id)] = True 

        # Always send response (don't throw an error)
        schema_url = reverse("navigator:codingschema-details", args=[self.project.id, schema.id])

        return HttpResponse(
            json.dumps({
                "fields" : errors, "schema_url" : schema_url,
                "rules_valid" : codingruletoolkit.schemarules_valid(schema)
            }),
            content_type='application/json'
        )

    def _get_schemafield_forms(self, fields):
        schema = self.get_object()
        for field in fields:
            field["codingschema"] = schema.id
            instance = CodingSchemaFieldForm._meta.model.objects.get(id=field["id"]) if "id" in field else None
            yield CodingSchemaFieldForm(schema, data=field, instance=instance)

def _get_form_errors(forms):
    """
    Check each form for errors. If an error is found in a form, a tuple
    of the form:

      (fieldnr, errors_dict)

    is yielded.
    """
    return ((f.data.get('fieldnr') or f.data["label"], f.errors) for f in forms if not f.is_valid())


def _get_form(data, schema, form):
    data["codingschema"] = schema.id
    instance = form._meta.model.objects.get(id=data["id"]) if "id" in data else None
    return form(schema, data=data, instance=instance)

def _get_forms(datas, schema, form):
    return map(partial(_get_form, form=form, schema=schema), datas)


class CodingSchemaFieldForm(forms.ModelForm):
    label = forms.CharField()
    default = forms.CharField(required=False)

    def __init__(self, schema, *args, **kwargs):
        super(CodingSchemaFieldForm, self).__init__(*args, **kwargs)
        self.fields['codebook'].required = False
        self.fields['codebook'].queryset = schema.project.get_codebooks()

    def save(self, commit=True):
        if self.cleaned_data['codebook'] is None:
            self.instance.codebook = None
        return super().save(commit=commit)

    def _to_bool(self, val):
        if val is None:
            return

        if str(val).lower() in ("true", "1", "yes"):
            return True
        elif str(val).lower() in ("false", "0", "no"):
            return False

    def clean_codebook(self):
        db_type = CodingSchemaFieldType.objects.get(name__iexact="Codebook")

        if 'fieldtype' not in self.cleaned_data:
            raise ValidationError("Fieldtype must be set in order to check this field")
        elif self.cleaned_data['fieldtype'] == db_type:
            if not self.cleaned_data['codebook']:
                raise ValidationError("Codebook must be set when fieldtype is '{}'".format(db_type))
        elif self.cleaned_data['codebook']:
            raise ValidationError("Codebook must not be set when fieldtype is '{}'".format(self.cleaned_data['fieldtype']))

        return self.cleaned_data['codebook']

    def clean_default(self):
        # Differentiate between '' and None
        value = self.cleaned_data['default']

        if 'fieldtype' not in self.cleaned_data:
            raise ValidationError("Fieldtype must be set in order to check this field")

        if self.data['default'] is None:
            return

        # Fieldtype is set
        fieldtype = self.cleaned_data['fieldtype']
        if fieldtype.serialiserclass == BooleanSerialiser:
            value = self._to_bool(value)

            if value is None:
                raise ValidationError(
                    ("When fieldtype is of type {}, default needs " +
                    "to be empty, true or false.").format(fieldtype))

        serialiser = fieldtype.serialiserclass(CodingSchemaField(**self.cleaned_data))

        try:
            return serialiser.serialise(value)
        except:
            if fieldtype.serialiserclass == CodebookSerialiser:
                try:
                    value = int(value)
                except ValueError:
                    raise ValidationError("This value needs to be a code_id.")

                # possible_values doesn't return a queryset, so we need to iterate :(
                if value in (code.id for code in serialiser.possible_values):
                    return value

                raise ValidationError("'{}' is not a valid value.".format(value))

            # Can't catch specific error
            possible_values = serialiser.possible_values

            if possible_values is not None:
                raise ValidationError(
                    "'{}' is not a valid value. Options: {}".format(
                        self.cleaned_data['default'], possible_values
                    )
                )

            raise ValidationError("'{}' is not a valid value".format(value))

    class Meta:
        model = CodingSchemaField
        exclude = ()

class CodingRuleForm(forms.ModelForm):
    def __init__(self, codingschema, *args, **kwargs):
        super(CodingRuleForm, self).__init__(*args, **kwargs)
        self.fields["action"].required = False
        self.fields["field"].required = False
        self.fields["field"].queryset = codingschema.fields.all()

        self.codingschema = codingschema

    def clean_condition(self):
        condition = self.cleaned_data["condition"]

        try:
            tree = codingruletoolkit.parse(CodingRule(condition=condition))
        except (Code.DoesNotExist, CodingSchemaField.DoesNotExist, CodingRule.DoesNotExist) as e:
            raise ValidationError(e)
        except SyntaxError as e:
            raise ValidationError(e)

        if tree is not None:
            codingruletoolkit.clean_tree(self.codingschema, tree)

        return condition

    class Meta:
        model = CodingRule
        exclude = ()


_get_schemafield_forms = partial(_get_forms, form=CodingSchemaFieldForm)
_get_codingrule_forms = partial(_get_forms, form=CodingRuleForm)

class CodingSchemaEditRulesView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, TemplateView):
    required_project_permission = PROJECT_ROLES.WRITER
    parent = CodingSchemaDetailsView
    url_fragment = "rules"
    form_class = CodingSchemaForm

    def get_context_data(self, **kwargs):
        ctx = super(CodingSchemaEditRulesView, self).get_context_data(**kwargs)
        ctx["codingschema"] = self.get_object()
        return ctx

    def get(self, *args, **kargs):
        if self.get_object().project != self.project:
            # Offer to copy it to currect project
            pass#return redirect(copy_schema, project.id, schema.id)
        return super(CodingSchemaEditRulesView, self).get(*args, **kargs)

    def post(self, commit, *args, **kwargs):
        request, schema, project = self.request, self.get_object(), self.project

        commit = request.GET.get("commit", commit) in (True, "true")
        rules = json.loads(request.POST['rules'])
        forms = list(_get_codingrule_forms(rules, schema))
        errors = dict(_get_form_errors(forms))

        if not errors and commit:
            rules = [form.save() for form in forms]

            for rule in set(schema.rules.all()) - set(rules):
                rule.delete()

            request.session["rules_{}_edited".format(schema.id)] = True

        # Always send response (don't throw an error)
        schema_url = reverse("navigator:codingschema-details", args=[project.id, schema.id])

        return HttpResponse(
            json.dumps(dict(fields=errors, schema_url=schema_url)),
            content_type='application/json'
        )



class CodingSchemaLinkView(ProjectFormView):
    required_project_permission = PROJECT_ROLES.WRITER
    parent = CodingSchemaListView
    url_fragment = 'link'

    class form_class(forms.Form):
        schemas = forms.MultipleChoiceField(widget=widgets.BootstrapMultipleSelect)

    def get_form(self, form_class=None):
        form = super(CodingSchemaLinkView, self).get_form(form_class)
        from navigator.forms import gen_coding_choices
        form.fields['schemas'].choices = gen_coding_choices(self.request.user, CodingSchema)
        return form

    def form_valid(self, form):
        schemas = form.cleaned_data['schemas']
        for cb in schemas:
            self.project.codingschemas.add(cb)
        self.request.session['notification'] = "Linked {n} codebook(s)".format(n=len(schemas))
        return super(CodingSchemaLinkView, self).form_valid(form)

class CodingSchemaUnlinkView(ProjectActionRedirectView):
    required_project_permission = PROJECT_ROLES.WRITER
    parent = CodingSchemaDetailsView
    url_fragment = "unlink"

    def action(self, project, codingschema):
        schema = CodingSchema.objects.get(pk=codingschema)
        project = Project.objects.get(pk=project)
        project.codingschemas.remove(schema)

    def get_redirect_url(self, **kwargs):
        return CodingSchemaListView._get_breadcrumb_url(kwargs, self)
        
