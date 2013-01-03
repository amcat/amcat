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

from django.shortcuts import render
from amcat.models.coding import codingtoolkit
from django.http import HttpResponse
from amcat.scripts.output.datatables import TableToDatatable
import datetime

def index(request):
    """show the main HTML"""
    return render(request, "annotator/overview.html")
    
    
def table(request):
    """returns a DataTable JSON table with a list of recent codingjobs"""
    startDate = datetime.datetime.now() - datetime.timedelta(days=365) # only show jobs from the past year
    table = codingtoolkit.get_table_jobs_per_user(request.user, insertdate__gt=startDate) 
    out = TableToDatatable().run(table)
    response = HttpResponse(mimetype='text/plain')
    response.write(out)
    return response
