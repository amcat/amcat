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
import logging

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect

from amcat.models.user import User
from api.rest.datatable import Datatable
from api.rest.resources import ProjectResource
from navigator import forms

log = logging.getLogger(__name__)

def view(request, id=None, form=None):
    if id is None:
        return redirect(reverse("navigator:user", args=[request.user.id]))

    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        raise Http404("User not found")

    if not (user == request.user or request.user.is_staff):
        raise PermissionDenied("You are not allowed to view other user's details.")

    ref = request.META.get('HTTP_REFERER', '')
    success = ref.endswith(reverse("navigator:user", args=[user.id])) and not form
    form = form or forms.UserDetailsForm(request, instance=user)

    # Generate projects-table javascript
    projects = Datatable(ProjectResource).filter(projectrole__user=user)
    main_active = "Current User" if user == request.user else "Users"

    return render(request, "user_view.html", {'user': user,
                                              'form': form,
                                              'projects': projects,
                                              'success': success,
                                              'main_active': main_active})

def edit(request, id):
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        return HttpResponse('User not found', status=404)

    if not (request.user.is_superuser or request.user.id == user.id):
        raise PermissionDenied("You cannot edit this user's profile.")

    form = forms.UserDetailsForm(request, data=request.POST or None, instance=user)
    if form.is_valid():
        form.save()
        return redirect(reverse("navigator:user", args=[user.id]))
    return view(request, id=user.id, form=form)

