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

from django.contrib.auth.models import User
from django.db.models import Q
from django.forms.widgets import HiddenInput

from amcat import models
from amcat.scripts import article_upload
from amcat.tools import toolkit

from django.core.exceptions import ValidationError

from amcat.models.authorisation import Role, ProjectRole
from amcat.models.user import Affiliation
from amcat.models.articleset import ArticleSet
from amcat.models.language import Language
from amcat.models.coding.codebook import Codebook, CodebookBase, CodebookCode
from amcat.models.coding.code import Code
from amcat.models.coding.codingschema import CodingSchema
from amcat.models.coding.codingschemafield import CodingSchemaField, CodingSchemaFieldType
from amcat.models.coding.codingjob import CodingJob
from amcat.models.coding.serialiser import BooleanSerialiser, CodebookSerialiser

from navigator.utils.auth import get_request
from navigator.utils.misc import cache_function

from amcat.forms import widgets, fields, forms

import zipfile

import logging; logger = logging.getLogger(__name__)

name_sort = lambda x: x[0].name.lower()

ALLOWED_EXTENSIONS = ('txt', 'csv', 'dat')
_ADMIN_ID = None
def get_admin_id():
    global _ADMIN_ID
    if _ADMIN_ID is None:
        _ADMIN_ID = Role.objects.get(label="admin", projectlevel=False).id
    return _ADMIN_ID

@cache_function(60)
def gen_user_choices(project=None):
    """This function generates a list of users formatted in such a
    way it's usable for a Django Choicefield.

    See: https://docs.djangoproject.com/en/dev/ref/models/fields/#field-choices"""
    users = User.objects.all().select_related('userprofile__affiliation__name').only(
        'username', 'first_name', 'last_name' 
    )

    users = users.filter(projectrole__project=project) if project else users
    vals = toolkit.multidict(((u.userprofile.affiliation, u) for u in users), ltype=list)

    for aff, users in sorted(vals.items(), key=name_sort):
        yield(aff, [(u.id, "%s - %s %s (%s)" % (u.id, u.first_name, u.last_name, u.username)) for u in users])

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
        Q(project__guest_role__id__gte=user.get_profile().role.id)
    ) if not user.get_profile().role.id >= get_admin_id() else model.objects.all()

    objects.select_related("project__name").only("name")
    objects = toolkit.multidict(((cb.project, cb) for cb in objects), ltype=list)

    for project, objs in sorted(objects.items(), key=name_sort):
        yield(project, [(x.id, x.name) for x in objs])


class UserForm(forms.ModelForm):
    affiliation = forms.ModelChoiceField(queryset=Affiliation.objects.all())
    role = forms.ModelChoiceField(queryset=Role.objects.all())
    language = forms.ModelChoiceField(queryset=Language.objects.all())

    def __init__(self, request, editing=True, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)

        if not request.user.is_anonymous():
            uprofile = request.user.get_profile()

            # Only show roles lesser or equal to the current role of the user
            self.fields['role'].queryset = Role.objects.filter(
                projectlevel=False, id__lte=uprofile.role.id
            )

            # Set initial values for this user
            self.fields['role'].initial = uprofile.role if not editing else kwargs['instance'].get_profile().role
            self.fields['affiliation'].initial = uprofile.affiliation
            self.fields['language'].initial = uprofile.language

        # We don't use Django groups and permissions
        for fi in ("groups", "user_permissions"):
            if fi in self.fields:
                del self.fields[fi]

        if editing:
            del self.fields["username"]

    def save(self, commit=True):
        u = super(UserForm, self).save(commit)

        up = u.get_profile()
        up.affiliation = self.cleaned_data['affiliation']
        up.role = self.cleaned_data['role']
        up.language = self.cleaned_data['language']
        up.save()

        return u

    class Meta:
        model = User

class UserDetailsForm(UserForm):
    def __init__(self, request, *args, **kwargs):
        super(UserDetailsForm, self).__init__(request, True, *args, **kwargs)
        for name in ["password", "is_staff", "is_superuser", "last_login", "date_joined"]:
            del self.fields[name]


class AddUserForm(UserForm):
    def __init__(self, request, *args, **kwargs):
        super(AddUserForm, self).__init__(request, False, *args, **kwargs)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

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

    def clean_owner(self):
        self.cleaned_data = User.objects.get(id=self.cleaned_data['owner'])
        return self.cleaned_data

class AddProjectForm(ProjectForm):
    owner = forms.ChoiceField(widget=widgets.JQuerySelect)

    def __init__(self, owner=None, *args, **kwargs):
        super(AddProjectForm, self).__init__(*args, **kwargs)
        self.fields['owner'].initial = owner.id if owner else None

class ProjectRoleForm(forms.ModelForm):
    user = forms.MultipleChoiceField(widget=widgets.JQueryMultipleSelect)

    def __init__(self, project=None, user=None, data=None, **kwargs):
        super(ProjectRoleForm, self).__init__(data=data, **kwargs)

        self.fields['user'].choices = gen_user_choices()

        if project is not None:
            # Disable self.project
            del self.fields['project']

            choices = ((r.id, r.label) for r in Role.objects.filter(projectlevel=True))
            self.fields['role'].choices = choices

            if user is not None:
                del self.fields['user']

    class Meta:
        model = ProjectRole

class UploadScriptForm(forms.Form):
    file = forms.FileField(help_text="Supported archives: zip")
    encoding = forms.ChoiceField(choices=((1, "ISO-8859-15"), (2, "UTF-8"), (3, "LATIN-1")),
                                 initial=1, help_text="Try to change this value when character"+
                                                      " issues arise.")


    exi_set = forms.ModelChoiceField(queryset=ArticleSet.objects.all(),
                                     label="Existing set", required=False)

    new_set = forms.CharField(max_length=100, required=False)
    script = forms.ChoiceField(choices=[(sc, sc) for sc in article_upload.__all__])

    def __init__(self, project, *args, **kwargs):
        super(UploadScriptForm, self).__init__(*args, **kwargs)

        exi = self.fields['exi_set']
        exi.queryset = exi.queryset.filter(project=project)

        self.project = project

    def _get_zip_files(self, fo):
        zip = zipfile.ZipFile(fo)

        for fi in zip.infolist():
            if fi.filename.split('.')[-1].lower in ALLOWED_EXTENSIONS:
                yield fi.filename, zip.read(fi)
            else:
                logger.debug("%s not in ALLOWED_EXTENSIONS, skipping.." % fi.filename)

    def clean_new_set(self):
        if not (self.cleaned_data['new_set'] or self.cleaned_data['exi_set']):
            raise forms.ValidationError("Either choose an existing set from the list above or\
                                         fill in this field to create a new set.")

        new_set = ArticleSet.objects.filter(project=self.project,
                                            name=self.cleaned_data['new_set'])

        if len(new_set) != 0:
            raise forms.ValidationError("Set already exists!")

        return self.cleaned_data['new_set']


    def clean_file(self):
        data = self.cleaned_data['file']
        ext = unicode(data).split('.')[-1]

        if ext.lower() not in ALLOWED_EXTENSIONS + ['zip']:
            raise forms.ValidationError("%s is not a supported format" % ext)

        # Extract all txt-files from archive
        if ext.lower() == 'zip':
            try:
                return list(self._get_zip_files(data))
            except zipfile.BadZipfile:
                raise forms.ValidationError("%s is not a zipfile" % data)

        # Read txt file
        elif ext.lower() in ALLOWED_EXTENSIONS:
            return [(unicode(data), data.read())]

    def clean_encoding(self):
        ident = self.cleaned_data['encoding']
        enc = dict(self.fields['encoding'].choices).get(int(ident))

        if 'file' not in self.cleaned_data:
            # Fail silently, as 'file' will fail anyway
            return enc

        # Test encoding
        for fn, bytes in self.cleaned_data['file']:
            try:
                bytes.decode(enc)
            except UnicodeDecodeError:
                raise ValidationError("Couldn't decode '%s' with '%s'" % (fn, enc))

        return enc

class MediumForm(forms.ModelForm):
    class Meta:
        model = models.medium.Medium

class CodingJobForm(forms.ModelForm):
    unitschema = forms.ModelChoiceField(CodingSchema.objects.none(), widget=widgets.JQuerySelect)
    articleschema = forms.ModelChoiceField(CodingSchema.objects.none(), widget=widgets.JQuerySelect)
    coder = forms.ModelChoiceField(User.objects.none(), widget=widgets.JQuerySelect)
    articleset = forms.ModelChoiceField(ArticleSet.objects.none(), widget=widgets.JQuerySelect)

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

class ImportCodebook(forms.Form):
    codebooks = forms.MultipleChoiceField(widget=widgets.JQueryMultipleSelect)

    def __init__(self, user, *args, **kwargs):
        super(ImportCodebook, self).__init__(*args, **kwargs)
        self.fields['codebooks'].choices = gen_coding_choices(user, Codebook)

class ImportCodingSchema(forms.Form):
    schemas = forms.MultipleChoiceField(widget=widgets.JQueryMultipleSelect)

    def __init__(self, user, *args, **kwargs):
        super(ImportCodingSchema, self).__init__(*args, **kwargs)
        self.fields['schemas'].choices = gen_coding_choices(user, CodingSchema)

class CodebookBaseForm(forms.ModelForm):

    def __init__(self, options=None, codebook=None):
        super(CodebookBaseForm, self).__init__(options)
        if codebook:
            self.fields["codebook"].initial = codebook
            self.fields["codebook"].widget = HiddenInput()
            imported = [c.id for c in codebook.project.codebooks.all()]
            bases = [b.base_id for b in codebook.codebookbases.all()]

            self.fields["base"].queryset = (Codebook.objects.filter(Q(project=codebook.project)
                                                                    |Q(id__in=imported))
                                            .exclude(id=codebook.id)
                                            .exclude(id__in=bases))


    class Meta:
        model = CodebookBase

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

class CodingSchemaFieldForm(forms.ModelForm):
    label = forms.CharField()
    default = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(CodingSchemaFieldForm, self).__init__(*args, **kwargs)
        self.fields['codebook'].required = False

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
                raise ValidationError("Setting codebook defaults not yet implemented")

            # Can't catch specific error
            possible_values = serialiser.possible_values

            if possible_values is not None:
                raise ValidationError(
                    "'{}' is not a valid value. Options: {}".format(
                        self.cleaned_data['default'], possible_values
                    )
                )

            raise ValidationError("'{}' is not a valid value".format(value))

        return value

    class Meta:
        model = CodingSchemaField
