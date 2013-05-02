###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                        #
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
from navigator.utils.misc import session_pop

from navigator import forms
from settings.menu import USER_MENU

import smtplib, itertools

from django import db
from django import http

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
    form = form or forms.UserDetailsForm(request, instance=user)

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
    form = forms.UserDetailsForm(request, data=request.POST or None, instance=user)
    if form.is_valid():
        form.save()
        return redirect(reverse(view, args=[user.id]))
    return view(request, id=user.id, form=form)

@check(User, action='create', args=None)
def add(request):
    add_form = forms.AddUserForm(request)
    add_multiple_form = forms.AddMultipleUsersForm(request)

    message = session_pop(request.session, "users_added")
    return render(request, "navigator/user/add.html", locals())

@db.transaction.commit_on_success
def _add_multiple_users(request):
    amf = forms.AddMultipleUsersForm(request, data=request.REQUEST, files=request.FILES)

    if amf.is_valid():
        props = dict(
            affiliation=amf.cleaned_data['affiliation'],
            language=amf.cleaned_data['language'],
            role=amf.cleaned_data['role']
        )

        for user in amf.cleaned_data['csv']:
            create_user(**dict(itertools.chain(props.items(), user.items())))

        request.session['users_added'] = ("Succesfully added {} user(s)"
                                            .format(len(amf.cleaned_data['csv'])))

        # Users created
        return redirect(reverse(add))

    return amf, forms.AddUserForm(request)

@db.transaction.commit_on_success
def _add_one_user(request):
    af = forms.AddUserForm(request, data=request.REQUEST)

    if af.is_valid():
        create_user(**af.clean())
        request.session['users_added'] = "Succesfully added user"
        return redirect(reverse(add))

    return forms.AddMultipleUsersForm(request), af


@check(User, action='create', args=None)
def add_submit(request):
    # Determine whether to create one or multiple users
    func = _add_one_user
    if request.REQUEST.get('submit-multiple'):
        func = _add_multiple_users

    # Try to add them
    try:
        resp = func(request)
    except smtplib.SMTPException as e:
        log.exception()
        message = ("Could not send e-mail. If this this error "
                    + "continues to exist, contact your system administrator")
    except db.utils.DatabaseError as e:
        # Duplicate users?
        message = "A database error occured. Try again?"
    else:
        if isinstance(resp, http.HttpResponseRedirect):
            return resp

        # Validation failed.
        amf, af = resp
        
    return render(request, "navigator/user/add.html", {
        'error' : locals().get('message'),
        'add_multiple_form' : amf,
        'add_form' : af,
    })
