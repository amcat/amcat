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

"""
Contains only the html representation of the selection form. 
The main selection code is found in the api/webscripts folder
"""

from django.shortcuts import render

from api.webscripts import mainScripts
from amcat.scripts.forms import SelectionForm


import logging
log = logging.getLogger(__name__)



def index(request):
    """returns the selection form"""
    outputs = []
    for ws in mainScripts:
        outputs.append({'id':ws.__name__, 'name':ws.name, 'formAsHtml': ws.formHtml()})
    
    context = {'form':SelectionForm(request.REQUEST), 'outputs':outputs}
    return render(request, 'navigator/selection/form.html', context)
    
    
    


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
    
from amcat.tools import amcattest
import base64

class TestSelectionView(amcattest.PolicyTestCase):
    fixtures = ['user.json'] # contains user test123
    
    def setUp(self):
        # self.user = amcattest.create_test_user()
        # self.user.set_password('pass123')
        self.headers = {'HTTP_AUTHORIZATION': 'Basic ' + base64.b64encode('test123:pass123')}
        
    # def tearDown(self):
        # self.user.delete()

    def test_index(self):
        """ tests if the selection page can be loaded"""
        # Issue a GET request.
        response = self.client.get('/navigator/selection', **self.headers)

        # Check that the response is 200 OK.
        self.assertEqual(response.status_code, 200)

        # Check that the rendered context contains output scripts
        self.assertIsNotNone(response.context['outputs'])
        
        self.assertContains(response, 'form')
