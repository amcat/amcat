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
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse

from api.rest import Datatable
from api.rest.resources import UserResource, ProjectResource

from amcat.models.user import User, Affiliation
from amcat.models.language import Language
from navigator.utils.auth import check, create_user, check_perm

from navigator import forms
from settings.menu import USER_MENU

def _table_view(request, table, selected=None, menu=USER_MENU):
    return render(request, "navigator/user/table.html", locals())

def _list_users(request, selected, **filters):
    return _table_view(request, Datatable(UserResource).filter(**filters), selected)

@check_perm("view_users_same_affiliation")
def my_affiliated_active(request):
    return _list_users(request, "active affiliated users", is_active=True,
                       userprofile__affiliation=request.user.get_profile().affiliation)

@check_perm("view_users_same_affiliation")
def my_affiliated_all(request):
    return _list_users(request, "all affiliated users",
                       affiliation=request.user.get_profile().affiliation)

@check_perm("view_users")
def all(request):
    return _list_users(request, "all users")

@check(User)
def view(request, user=None, form=None):
    if user is None:
        return redirect(reverse(view, args=[request.user.id]))

    ref = request.META.get('HTTP_REFERER', '')
    success = ref.endswith(reverse(view, args=[user.id])) and not form
    form = form or forms.UserForm(request, instance=user)

    # Generate projects-table javascript
    projects = Datatable(ProjectResource).filter(projectrole__user=user)
    menu = None if user == request.user else USER_MENU

    return render(request, "navigator/user/view.html", {'user' : user,
                                                        'form' : form,
                                                        'projects' : projects,
                                                        'success' : success,
                                                        'menu' : menu})

@check(User, action='update')
def edit(request, user):
    form = forms.UserForm(request, data=request.POST or None, instance=user)
    if form.is_valid():
        form.save()
        return redirect(reverse(view, args=[user.id]))
    return view(request, id=user.id, form=form)

@check(User, action='create', args=None)
def add(request):
    add_form = forms.AddUserForm(request)
    add_multiple_form = forms.AddMultipleUsersForm(request)

    return render(request, "navigator/user/add.html", locals())

@check(User, action='create', args=None)
def add_submit(request):
    req = request.REQUEST

    if req.get('submit-multiple'):
        amf = forms.AddMultipleUsersForm(request, data=req, files=request.FILES)
        if amf.is_valid():
            for user in amf.cleaned_data['csv']:
                create_user(
                    affiliation=amf.cleaned_data['affiliation'],
                    language=amf.cleaned_data['language'],
                    role=amf.cleaned_data['role'],
                    **user
                )

            return redirect(reverse('navigator.views.report.users'))
        
        af = forms.AddUserForm(request)
    else:
        af = forms.AddUserForm(request, data=request.REQUEST)

        if af.is_valid():
            data = af.clean()

            u = create_user(
                data['username'], data['first_name'], data['last_name'],
                data['email'], data['affiliation'], data['language'],
                data['role']
            )

            return redirect(reverse(add))

        amf = forms.AddMultipleUsersForm(request)

    return render(request, "navigator/user/add.html", {
        'add_multiple_form' : amf,
        'add_form' : af
    })
