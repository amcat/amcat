from django import forms
from webscript import WebScript
from django.template.loader import render_to_string

import amcat.scripts.forms
import amcat.forms

from amcat.scripts import script

#from amcat.scripts.searchscripts.articlelist import ArticleListScript, ArticleListSpecificForm


    
class ShowSummary(WebScript):
    name = "Summary"
    form_template = None
    form = None
    
    def run(self):
        form = amcat.scripts.forms.SelectionForm(self.formData) # check form here already, so no invalid ajax requests will be made later
        if not form.is_valid():
            raise amcat.forms.InvalidFormException("Invalid or missing options: %r" % form.errors, form.errors)
        return self.outputJsonHtml(render_to_string('api/webscripts/summary.html'))
        
        
