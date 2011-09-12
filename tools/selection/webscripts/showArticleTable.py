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

from django import forms
from amcat.tools.selection.webscripts.webscript import WebScript

class ListForm(forms.Form):
    detailed = forms.BooleanField(initial=False, required=False)
    start = forms.IntegerField(initial=0, min_value=0, widget=forms.HiddenInput)
    count = forms.IntegerField(initial=100, min_value=1, max_value=10000, widget=forms.HiddenInput)

    
class ShowArticleTable(WebScript):
    name = "Article Table"
    template = None
    form = ListForm
    #displayLocation = DISPLAY_IN_MAIN_FORM
    
    def run(self):
        articles = self.getArticles(start=0, length=100, highlight=False)
        return self.outputArticleTable(articles)
        