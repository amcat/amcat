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
from django.template.loader import render_to_string
from amcat.tools.selection.webscripts.webscript import WebScript
from amcat.model.project import Project
from django.http import HttpResponse
from amcat.tools.table.table3 import ObjectColumn, ObjectTable
from amcat.tools.table.tableoutput import table2csv
import csv

from openpyxl.workbook import Workbook
from openpyxl.writer.dump_worksheet import ExcelDumpWriter
import zipfile
from cStringIO import StringIO

    
class ExportArticles(forms.Form):
    columns = forms.MultipleChoiceField(
        choices=(
            ('articleid', 'Article ID'),
            ('date','Date'),
            ('mediumid','Medium ID'),
            ('mediumname','Medium Name'),
            ('projectid','Project ID'),
            ('projectname','Project Name'),
            ('pagenr','Page number'),
            ('section','Section'),
            ('length','Length'),
            ('url','url'),
            ('parentid','Parent Article ID'),
            ('externalid','External ID'),
            ('additionalMetadata','Additional Metadata'),
            ('headline','Headline'),
            ('text','Article Text')
        ),
        initial = ('articleid', 'date', 'mediumid', 'projectid')
    )
    limit = forms.ChoiceField(choices=((100,'100'),(1000,'1.000'),(10000,'10.000'),(100000,'100.000'),('nolimit', 'No limit')), initial=1000)
    limitTextLength = forms.BooleanField(initial=True, required=False)
    

class ExportArticles(WebScript):
    name = "Export Articles"
    template = "navigator/selection/webscripts/exportArticlesForm.html"
    form = ExportArticles
    displayLocation = ('ShowSummary', 'ShowArticleTable')
    id = 'ExportArticles'
    supportedOutputTypes = ('csv-tab', 'csv-semicolon', 'csv-comma','xlsx')
    
    def run(self):
        length = self.ownForm.cleaned_data['limit']
        if length == 'nolimit': length = -1
        articles = self.getArticles(start=0, length=length, highlight=False)
        
        cols = self.ownForm.cleaned_data['columns']
        
        if self.ownForm.cleaned_data['limitTextLength']:
            textLambda = lambda a:a.text[:31900]
        else:
            textLambda = lambda a:a.text
        
        output = self.generalForm.cleaned_data['output']
        
        colDict = { # mapping of names to article object attributes
            'articleid': ObjectColumn("id", lambda a: a.id),
            'date': ObjectColumn('Date', lambda a: a.date.strftime('%Y-%m-%d %H:%M')),
            'mediumid': ObjectColumn('Medium ID', lambda a:a.medium_id),
            'mediumname': ObjectColumn('Medium Name', lambda a:a.medium.name),
            'projectid': ObjectColumn('Project ID', lambda a:a.project_id),
            'projectname': ObjectColumn('Project Name', lambda a:a.project.name),
            'pagenr': ObjectColumn('Page number', lambda a:a.pagenr),
            'section': ObjectColumn('Section', lambda a:a.section),
            'length': ObjectColumn('Length', lambda a:a.length),
            'url': ObjectColumn('url', lambda a:a.url),
            'parentid': ObjectColumn('Parent Article ID', lambda a:a.parent_id),
            'externalid': ObjectColumn('External ID', lambda a:a.externalid),
            'additionalMetadata': ObjectColumn('Additional Metadata', lambda a:a.metastring),
            'headline': ObjectColumn('Headline', lambda a:a.headline),
            'text': ObjectColumn('Article Text', textLambda)
        }
        if output == 'xlsx':
            colDict['date'] = ObjectColumn('Date', lambda a: a.date)
        columns = [colDict[col] for col in cols]
        
        table = ObjectTable(articles, columns)
        
        
        
        
        if output == 'csv-tab':
            delimiter = '\t'
        elif output == 'csv-semicolon':
            delimiter = ';'
        elif output == 'csv-comma':
            delimiter = ':'
        
        if output == 'xlsx':
            wb = Workbook(optimized_write = True)
            ws = wb.create_sheet()
            for row in table.getRows():
                ws.append([table.getValue(row, column) for column in table.getColumns()])
            writer = ExcelDumpWriter(wb)
            response = HttpResponse(mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=exportArticles.xlsx'
            # need to do a little bit more work here, since the openpyxl library only supports writing to a filename, while we need a buffer here..
            buffer = StringIO()
            zf = zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED)
            writer.write_data(zf)
            zf.close()
            buffer.flush()
            buffervalue = buffer.getvalue()
            buffer.close()
            response.write(buffervalue)
        else:
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = 'attachment; filename=exportArticles.csv'
            table2csv(table, csvwriter=csv.writer(response, dialect='excel', delimiter=delimiter), writecolnames=True, writerownames=False, tabseparated=False)
        
        return response
        
        
        
        
        