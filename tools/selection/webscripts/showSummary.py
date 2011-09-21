from django import forms
from amcat.tools.selection.webscripts.webscript import WebScript
from django.template.loader import render_to_string

class SummaryForm(forms.Form):
    start = forms.IntegerField(initial=0, min_value=0, widget=forms.HiddenInput)
    count = forms.IntegerField(initial=100, min_value=1, max_value=10000, widget=forms.HiddenInput)


class ShowSummary(WebScript):
    name = "Summary"
    template = None
    form = SummaryForm
    
    
    def run(self):
        articles = self.getArticles(start=0, length=30, highlight=True)
        stats = self.getStatistics()
        return self.outputArticleSummary(articles, stats)
        
    
    def outputArticleSummary(self, articles, stats=None):
        actions = self.getActions()
        return render_to_string('navigator/selection/articlesummary.html', { 'articles': articles, 'stats':stats, 'actions':actions, 'generalForm':self.generalForm, 'ownForm':self.ownForm})
        