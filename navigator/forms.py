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

import logging;

from django.contrib.auth.models import User
from django.db.models import Q
from django.forms.widgets import HiddenInput

from amcat import models
from amcat.forms import widgets, fields, forms
from amcat.models.article import Article
from amcat.models.articleset import ArticleSet
from amcat.models.authorisation import Role
from amcat.models.coding.code import Code
from amcat.models.coding.codebook import Codebook, CodebookCode
from amcat.models.coding.codingjob import CodingJob
from amcat.models.coding.codingschema import CodingSchema
from amcat.models.language import Language
from amcat.models.project import Project
from amcat.models.user import THEMES
from amcat.tools import toolkit
from navigator.utils.misc import cache_function
from settings import MAX_SIGNUP_ROLEID

logger = logging.getLogger(__name__)

name_sort = lambda x: x[0].name.lower()

ALLOWED_EXTENSIONS = ('txt', 'csv', 'dat')
_ADMIN_ID = None
def get_admin_id():
    global _ADMIN_ID
    if _ADMIN_ID is None:
        _ADMIN_ID = Role.objects.get(label="admin", projectlevel=False).id
    return _ADMIN_ID

@cache_function(60)
def gen_user_choices(project):
    """This function generates a list of users formatted in such a
    way it's usable for a Django Choicefield.
    """

    #TODO! This used to yield affiliation, [users]
    users = users.filter(projectrole__project=project)
    yield("-", [(u.id, "%s - %s %s (%s)" % (u.id, u.first_name, u.last_name, u.username)) for u in users])

@cache_function(60)
def gen_roles():
    """Generate choices for UserForm.roles."""
    roles = Role.objects.filter(projectlevel=False)
    return ((r.id, r) for r in roles)

@cache_function(60)
def gen_coding_choices(user, model):
    # Get codebooks based on three
    objects = model.objects.filter(
        # User in project
        Q(project__projectrole__user=user)|
        # User has access to project through guestrole
        Q(project__guest_role__id__gte=user.userprofile.role.id)
    ).distinct() if not user.userprofile.role.id >= get_admin_id() else model.objects.all()

    objects.select_related("project__name").only("name")
    objects = toolkit.multidict(((cb.project, cb) for cb in objects), ltype=list)

    for project, objs in sorted(objects.items(), key=name_sort):
        yield(project, [(x.id, x.name) for x in objs])

class SplitArticleForm(forms.Form):
    add_to_new_set = forms.CharField(required=False)
    add_to_sets = forms.ModelMultipleChoiceField(queryset=ArticleSet.objects.none(), widget=widgets.BootstrapMultipleSelect, required=False)

    remove_from_sets = forms.ModelMultipleChoiceField(queryset=ArticleSet.objects.none(), widget=widgets.BootstrapMultipleSelect, required=False)
    remove_from_all_sets = forms.BooleanField(initial=True, required=False, help_text="Remove all instances of the original article in this project")

    add_splitted_to_sets = forms.ModelMultipleChoiceField(queryset=ArticleSet.objects.none(), widget=widgets.BootstrapMultipleSelect, required=False)
    add_splitted_to_new_set = forms.CharField(required=False)
    add_splitted_to_all = forms.BooleanField(initial=False, required=False, help_text="Add new (splitted) articles to all sets containing the original article")

    def __init__(self, project, article, *args, **kwargs):
        if not isinstance(project, Project):
            raise ValueError("First argument of constructor must be a Project")

        if not isinstance(article, Article):
            raise ValueError("Second argument of constructor must be a Article")

        super(SplitArticleForm, self).__init__(*args, **kwargs)
        self.fields["add_splitted_to_sets"].queryset = project.all_articlesets()
        self.fields["remove_from_sets"].queryset = project.all_articlesets().filter(articles=article)
        self.fields["add_to_sets"].queryset = project.all_articlesets()

class UserForm(forms.ModelForm):
    role = forms.ModelChoiceField(queryset=Role.objects.filter(projectlevel=False))
    language = forms.ModelChoiceField(queryset=Language.objects.all(), initial="en")

    def __init__(self, request, editing=True, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)

        if not request.user.is_anonymous():
            # Only show roles lesser or equal to the current role of the user
            uprofile = request.user.userprofile

            self.fields['role'].queryset = Role.objects.filter(
                projectlevel=False, id__lte=uprofile.role.id
            )

            # Set initial values for this user
            self.fields['role'].initial = uprofile.role if not editing else kwargs['instance'].userprofile.role
            self.fields['language'].initial = uprofile.language
            self.fields['theme'].initial = uprofile.theme
        else:
            # Only show roles appropriate for anonymous users
            self.fields['role'].queryset = Role.objects.filter(
                projectlevel=False, id__lte=MAX_SIGNUP_ROLEID
            )

        # We don't use Django groups and permissions
        for fi in ("groups", "user_permissions"):
            if fi in self.fields:
                del self.fields[fi]

    def save(self, commit=True):
        u = super(UserForm, self).save(commit)

        up = u.userprofile
        up.role = self.cleaned_data['role']
        up.language = self.cleaned_data['language']
        up.theme = self.cleaned_data['theme']
        up.save()

        return u

    class Meta:
        model = User
        fields = ("role", "language")

class UserDetailsForm(UserForm):
    def __init__(self, request, *args, **kwargs):
        super(UserDetailsForm, self).__init__(request, True, *args, **kwargs)


class AddUserForm(UserForm):
    def __init__(self, request, *args, **kwargs):
        super(AddUserForm, self).__init__(request, False, *args, **kwargs)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

class AddUserFormWithPassword(UserForm):
    def __init__(self, request, *args, **kwargs):
        super(AddUserFormWithPassword, self).__init__(request, False, *args, **kwargs)
    password = forms.CharField(label="Password",
                               widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repeat password",
                               widget=forms.PasswordInput)
    def clean_password(self):
        pwd1 = self.data['password']
        pwd2 = self.data['password2']
        if pwd1 != pwd2:
            raise forms.ValidationError("Passwords do not match")
        return pwd1
        
        
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password', 'password2')

        
class AddMultipleUsersForm(AddUserForm):
    csv = fields.CSVField(label="CSV", columns={
        'username' : fields.UserField(),
        'email' : forms.EmailField(),
        'last_name' : forms.CharField(),
        'first_name' : forms.CharField(),
    })

    delimiter = forms.CharField(initial=',',
                    help_text="This field indicates how this CSV is splitted.")

    def __init__(self, request, *args, **kwargs):
        super(AddMultipleUsersForm, self).__init__(request, *args, **kwargs)

        for field in ("username", "email", "last_name", "first_name"):
            del self.fields[field]

    def full_clean(self, *args, **kwargs):
        self.fields['csv'].set_delimiter(self.data.get('delimiter', ','))
        return super(AddMultipleUsersForm, self).full_clean(*args, **kwargs)

class ProjectForm(forms.ModelForm):
    guest_role = forms.ModelChoiceField(queryset=Role.objects.filter(projectlevel=True),
                                        required=False, help_text="Leaving this value \
                                        empty means it will not be readable at all.",
                                        initial=11)

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)

        for fld in ('codingschemas', 'codebooks', 'owner'):
            del self.fields[fld]

    class Meta:
        model = models.project.Project
        exclude = ("codingschemas", "codebooks", "owner")

    def clean_owner(self):
        self.cleaned_data = User.objects.get(id=self.cleaned_data['owner'])
        return self.cleaned_data

class AddProjectForm(ProjectForm):
    owner = forms.ChoiceField(widget=widgets.BootstrapSelect)

    def __init__(self, owner=None, *args, **kwargs):
        super(AddProjectForm, self).__init__(*args, **kwargs)
        self.fields['owner'].initial = owner.id if owner else None


class CodingJobForm(forms.ModelForm):
    unitschema = forms.ModelChoiceField(CodingSchema.objects.none(), widget=widgets.BootstrapSelect)
    articleschema = forms.ModelChoiceField(CodingSchema.objects.none(), widget=widgets.BootstrapSelect)
    coder = forms.ModelChoiceField(User.objects.none(), widget=widgets.BootstrapSelect)
    articleset = forms.ModelChoiceField(ArticleSet.objects.none(), widget=widgets.BootstrapSelect)

    def __init__(self, edit=True, project=None, **kwargs):
        """
        @type edit: boolean
        @param edit: Is this form used to edit a CodingJob?
        """
        super(CodingJobForm, self).__init__(**kwargs)

        project = project or self.instance.project

        # These field are mandatory for ArticleSet, but implicit for every
        # form initialized
        del self.fields['insertuser']
        del self.fields['project']

        if edit is True:
            # Codingjobs can't change articlesets while being coded
            del self.fields['articleset']
        else:
            # Only display articlesets in project
            qs = ArticleSet.objects.filter(Q(project=project) | Q(projects_set=project))
            self.fields['articleset'].queryset = qs

        schemas_qs = project.get_codingschemas()

        # Select choices available in project
        self.fields['coder'].queryset = User.objects.filter(projectrole__project=project)
        self.fields['coder'].choices = gen_user_choices(project)
        self.fields['unitschema'].queryset = schemas_qs.filter(isarticleschema=False)
        self.fields['articleschema'].queryset = schemas_qs.filter(isarticleschema=True)

    class Meta:
        model = CodingJob
        exclude = ()


class ImportCodingSchema(forms.Form):
    schemas = forms.MultipleChoiceField(widget=widgets.BootstrapMultipleSelect)

    def __init__(self, user, *args, **kwargs):
        super(ImportCodingSchema, self).__init__(*args, **kwargs)
        self.fields['schemas'].choices = gen_coding_choices(user, CodingSchema)


def add_error(form, field, error):
    form.errors[field] = form.errors.get(field, []) + [error]
def remove_error(form, field, error):
    form.errors[field].remove(error)
    if not form.errors[field]: del form.errors[field]

class CodebookCodeForm(forms.ModelForm):
    def __init__(self, options=None, codebook=None):
        super(CodebookCodeForm, self).__init__(options)
        if codebook:
            self.fields["codebook"].initial = codebook
            self.fields["codebook"].widget = HiddenInput()
            self.fields["parent"].required = False # why is this even required???
            cids = codebook.get_code_ids()
            self.fields['parent'].queryset = self.fields['parent'].queryset.filter(id__in=cids)
            self.fields['code'].queryset = self.fields['code'].queryset.exclude(id__in=cids)

    class Meta:
        model = CodebookCode
        fields = ('codebook', 'code', 'parent')

class CodebookNewCodeForm(forms.Form):
    codebook = forms.ModelChoiceField(queryset=Codebook.objects.all())
    label = forms.CharField()
    language = forms.ModelChoiceField(queryset=Language.objects.all())
    parent = forms.ModelChoiceField(queryset=Code.objects.all(), required=False)

    def __init__(self, options=None, codebook=None):
        super(CodebookNewCodeForm, self).__init__(options)
        if codebook:
            self.fields["codebook"].initial = codebook
            self.fields["codebook"].widget = HiddenInput()
            self.fields['parent'].queryset = (self.fields['parent'].queryset
                                              .filter(id__in=codebook.get_code_ids()))

    def save(self):
        code = Code.create(label=self.cleaned_data['label'], language=self.cleaned_data['language'])
        self.cleaned_data['codebook'].add_code(code, self.cleaned_data.get('parent'))


    class Meta:
        model = CodebookCode
        fields = ('codebook', 'code', 'parent')

class ArticleSetForm(forms.ModelForm):
    class Meta:
        model = ArticleSet
        fields = ('project', 'name', 'provenance')

class CodingSchemaForm(forms.HideFieldsForm):
    class Meta:
        model = CodingSchema
        exclude = ()
