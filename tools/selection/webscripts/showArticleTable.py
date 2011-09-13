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
from amcat.tools.table.table3 import ObjectColumn, ObjectTable
from amcat.tools.table.tableoutput import yieldtablerows
from django.template.loader import render_to_string

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
        
    
       
    def outputArticleTable(self, articles):
        #articles = articles[:50] # todo remove limit
        
        columns = [
            ObjectColumn("id", lambda a: a.id),
            ObjectColumn("headline", lambda a: a.headline),#a.highlightedHeadline[0] if hasattr('a', 'highlightedHeadline') else a.headline), # does not work since gets stripped away later
            ObjectColumn("date", lambda a: a.date.strftime('%Y-%m-%d')),
            ObjectColumn("medium", lambda a: '%s - %s' % (a.medium.id, a.medium.name) ),
            ObjectColumn("length", lambda a: a.length)
        ]
        
        table = ObjectTable(articles, columns)
        tablerows = yieldtablerows(table) # helper function needed since Django does not support function calling in templates with 2 parameters...
        return render_to_string('navigator/selection/articletable.html', { 'table': table, 'tablerows':tablerows })
        
       