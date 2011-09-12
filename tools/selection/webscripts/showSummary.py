from django import forms
from amcat.tools.selection.webscripts.webscript import WebScript

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
        