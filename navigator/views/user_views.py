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
import datetime

from django import forms
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse
from django.forms import formset_factory
from django.utils.safestring import mark_safe
from django.views.generic import FormView
from django.views.generic.base import RedirectView
from django.views.generic.list import ListView
from rest_framework.authtoken.models import Token

from amcat.forms.widgets import BootstrapMultipleSelect
from amcat.models import Project, ProjectRole, Role
from amcat.models import User, authorisation
from api.rest.get_token import get_token
from api.rest.resources import ProjectRoleResource
from api.rest.tokenauth import EXPIRY_TIME
from navigator.forms import gen_user_choices
from navigator.utils import auth
from navigator.views.datatableview import DatatableMixin
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, BaseMixin

class UserTokenView(FormView):
    url_fragment = "tokens"
    template_name = "user_token.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if form.instance.pk and form.instance.created < datetime.datetime.now() - EXPIRY_TIME:
            form.fields['key'].help_text = mark_safe('<span class="text-danger">expired</span>')
        return form

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs["instance"] = Token.objects.get(user=self.request.user)
        except Token.DoesNotExist:
            pass
        return kwargs

    def form_valid(self, form):
        token = get_token(self.request.user)
        return super().form_valid(form)

    @classmethod
    def get_url_patterns(cls):
        yield "^user/tokens/$"

    @classmethod
    def get_view_name(cls):
        return "user-token"

    def get_success_url(self):
        return reverse("navigator:{}".format(self.get_view_name()))

    class form_class(forms.ModelForm):
        key = forms.CharField(required=False, widget=forms.TextInput(attrs={"readonly": "readonly"}))

        class Meta:
            model = Token
            fields = ("key",)

        def save(self, commit=True):
            return

class ProjectRoleForm(forms.ModelForm):
    user = forms.MultipleChoiceField(widget=BootstrapMultipleSelect)

    def __init__(self, project=None, user=None, data=None, **kwargs):
        super(ProjectRoleForm, self).__init__(data=data, **kwargs)

        self.fields['user'].choices = gen_user_choices()

        if project is not None:
            # Disable self.project
            del self.fields['project']

            choices = [(r.id, r.label) for r in Role.objects.all()] + [(None, "Remove user")]
            self.fields['role'].choices = choices

            if user is not None:
                del self.fields['user']

    class Meta:
        model = ProjectRole
        exclude = ()


class ProjectUserListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    required_project_permission = authorisation.ROLE_PROJECT_ADMIN
    model = User
    parent = None
    base_url = "projects/(?P<project>[0-9]+)"
    context_category = 'Settings'
    url_fragment = "users"
    resource = ProjectRoleResource

    @classmethod
    def get_view_name(cls):
        return "user-list"

    def get_context_data(self, **kwargs):
        context = super(ProjectUserListView, self).get_context_data(**kwargs)
        context['add_user'] = ProjectRoleForm(self.project)
        return context

    def filter_table(self, table):
        return table.filter(project=self.project).hide('project', 'id')


class ProjectUserAddView(ProjectViewMixin, HierarchicalViewMixin, RedirectView):
    required_project_permission = authorisation.ROLE_PROJECT_ADMIN
    parent = ProjectUserListView
    url_fragment = "add"
    model = User

    def get_redirect_url(self, project):
        project = Project.objects.get(id=project)
        role = self.request.POST['role']
        role = None if role == 'None' or role == "" else Role.objects.get(id=role)

        for user in User.objects.filter(id__in=self.request.POST.getlist('user')):
            try:
                r = ProjectRole.objects.get(project=project, user=user)
                if role is None:
                    r.delete()
                else:
                    r.role = role
                    r.save()
            except ProjectRole.DoesNotExist:
                if role is not None:
                    r = ProjectRole(project=project, user=user, role=role)
                    r.save()
        return reverse("navigator:user-list", args=[project.id])

class ProjectUserInviteForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    exists = forms.BooleanField(required=False, widget=forms.HiddenInput)

    def validate_unique(self):
        pass

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]

class ProjectUserInviteBaseFormSet(forms.BaseFormSet):

    @property
    def management_form(self):
        form = super().management_form
        form.fields["confirm"] = forms.BooleanField(widget=forms.HiddenInput)
        form.fields["role"] = forms.ModelChoiceField(queryset=Role.objects.all(), label="Project Role",
                                                     help_text="All selected users will have this role. Optional, leave blank if users shouldn't be added to the project.")
        return form

ProjectUserInviteFormSet = formset_factory(form=ProjectUserInviteForm, formset=ProjectUserInviteBaseFormSet, extra=1, min_num=1)

class ProjectUserInviteView(BaseMixin, FormView):
    required_project_permission = authorisation.ROLE_PROJECT_ADMIN
    form_class = ProjectUserInviteFormSet
    parent = ProjectUserListView
    url_fragment = "invite"
    confirm = False

    def has_permission(self, perm):
        if not self.request.user.is_staff:
            return False
        return super().has_permission(perm)

    def create_user(self, user_form):
        return auth.create_user(
            username=user_form.cleaned_data['username'],
            email=user_form.cleaned_data['email'],
            first_name=user_form.cleaned_data['first_name'],
            last_name=user_form.cleaned_data['last_name']
        )

    def form_confirmed(self, form):
        for f in form:
            try:
                user = User.objects.get(email=f.cleaned_data["email"])
                if not f.cleaned_data["exists"]:
                    raise SuspiciousOperation
            except User.DoesNotExist:
                if f.cleaned_data["exists"]:
                    raise SuspiciousOperation
                user = self.create_user(f)

            if form.data.get("form-role"):
                role = Role.objects.get(id=int(form.data["form-role"]))
                ProjectRole.objects.update_or_create(user=user, project=self.project, defaults={"role": role})

        return super().form_valid(form)

    def form_valid(self, form):
        # This form consists of two steps: a step where the users fills in the users, followed by validation
        # and a check for existing users on the server which must be confirmed by the user.
        # If the 'confirm' flag of the management_form is set this indicates that the confirmation step has
        # been completed.
        if bool(form.management_form.data.get('form-confirm')):
            return self.form_confirmed(form)
        self.confirm = True
        return self.form_confirm(form)

    def check_user_form(self, new_form_data, form_idx):
        data = new_form_data
        i = form_idx
        email = data.get('form-{}-email'.format(i))
        user = User.objects.filter(email=email)
        if user.exists():
            user = user.first()
            data['form-{}-username'.format(i)] = user.username
            data['form-{}-email'.format(i)] = email
            data['form-{}-first_name'.format(i)] = user.first_name
            data['form-{}-last_name'.format(i)] = user.last_name
            data['form-{}-exists'.format(i)] = True
            return True
        return False

    def form_confirm(self, form):
        data = form.data.copy()
        data['form-confirm'] = True
        fms = [f for f in form if f.cleaned_data]
        emails = set()
        for f in fms:
            emails.add(f.cleaned_data["email"])
        existing_users = {user.email: user for user in User.objects.filter(email__in=emails)}

        # check for existing users and flag them as such, change user info in form if necessary.
        for i in range(len(form.forms)):
            self.check_user_form(data, i)
            form.forms[i].data = data
            form.forms[i].initial = data
            for k, f in form.forms[i].fields.items():
                f.widget.attrs["readonly"] = "readonly"
                f.widget.attrs["class"] = "input-confirm"

        # strip unused forms
        n = len(form.forms)
        for i in range(len(form.forms) - 1, -1, -1):
            if data['form-{}-email'.format(i)] != '':
                break
            form.forms.pop(i)
            n -= 1
        data["form-TOTAL_FORMS"] = n
        form.management_form.data = data
        form.data = data
        form.initial = data
        return super().form_invalid(form) # return to form view

    def get_success_url(self):
        return reverse("navigator:user-list", args=[self.project.id])
