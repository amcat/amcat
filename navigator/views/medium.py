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

from navigator.forms import MediumForm, MediumAliasForm
from navigator.utils.auth import check_perm


@check_perm("manage_media")
def add(request):
    form = MediumForm(request.POST or None)
    
    if 'submit' in request.POST and form.is_valid():
        form.save()
        return redirect(reverse('media'))
        
    return render(request, "navigator/medium/add.html", dict(form=form))

@check_perm("manage_media")
def add_alias(request):
    form = MediumAliasForm(request.POST or None)

    if 'submit' in request.POST and form.is_valid():
        form.save()
        return redirect(reverse('media'))

    return render(request, "navigator/medium/add_alias.html",  dict(form=form))
