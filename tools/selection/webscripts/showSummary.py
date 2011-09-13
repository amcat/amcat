from django import forms
from amcat.tools.selection.webscripts.webscript import WebScript
from django.template.loader import render_to_string

class EmptyForm(forms.Form): pass

class ShowSummary(WebScript):
    name = "Summary"
    template = None
    form = EmptyForm
    #displayLocation = DISPLAY_IN_MAIN_FORM
    
    def run(self):
        articles = self.getArticles(start=0, length=30, highlight=True)
        stats = self.getStatistics()
        return self.outputArticleSummary(articles, stats)
        
    
    def outputArticleSummary(self, articles, stats=None):
        #articles = articles[:50] # todo remove limit
        return render_to_string('navigator/selection/articlesummary.html', { 'articles': articles, 'stats':stats })
        