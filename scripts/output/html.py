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

from amcat.tools.table import tableoutput
from amcat.tools.table import table3
from amcat.scripts import script, types
from django.utils import simplejson
import amcat.scripts.forms
from django.template.loader import render_to_string
from django import forms
import base64

import logging
log = logging.getLogger(__name__)



class HtmlTemplateForm(forms.Form):
    template = forms.CharField(required=False)
    
    
                    
class ObjectToHtml(script.Script):
    """ general script that can be used to render any object as html, using a template"""
    input_type = object
    options_form = HtmlTemplateForm
    output_type = types.HtmlData


    def run(self, obj):
        return render_to_string(self.options['template'], {'object':obj})
        
        

class TableToHtml(script.Script):
    input_type = table3.Table
    options_form = HtmlTemplateForm
    output_type = types.HtmlData


    def run(self, tableObj):
        if self.options['template']:
            return render_to_string(self.options['template'], {'table':tableObj})
        return tableoutput.table2htmlDjango(tableObj)
       
       
       
class ArticleListToHtml(script.Script):
    input_type = types.ArticleIterator
    options_form = HtmlTemplateForm
    output_type = types.HtmlData


    def run(self, articlelist):
        return render_to_string(self.options['template'], {'articlelist':articlelist})
        
        
        
class ArticleSetStatisticsToHtml(script.Script):
    input_type = types.ArticleSetStatistics
    options_form = HtmlTemplateForm
    output_type = types.HtmlData


    def run(self, statsObj):
        return render_to_string(self.options['template'], {'stats':statsObj})
        
        
                
class ImageMapToHtml(script.Script):
    input_type = types.ImageMap
    options_form = HtmlTemplateForm
    output_type = types.HtmlData


    def run(self, imagemapObj):
        imgBase64 = base64.encodestring(imagemapObj.image)
        articleCount = imagemapObj.articleCount
        mapHtml = imagemapObj.mapHtml
        tableHtml = TableToHtml().run(imagemapObj.table)
        return render_to_string(self.options['template'], 
                                    {'imgBase64':imgBase64, 
                                    'articleCount':articleCount, 
                                    'mapHtml':mapHtml,
                                    'tableHtml':tableHtml
                                   })
        
        
        
class ErrormsgToHtml(script.Script):
    input_type = types.ErrorMsg
    options_form = None
    output_type = types.HtmlData
    
    def run(self, errorMsg):
        return simplejson.dumps({'error':{'message':errorMsg.message}}) # BUG: this is not html...