from django import forms
from amcat.tools.selection.webscripts.webscript import WebScript
from django.template.loader import render_to_string
from django.utils import simplejson
from django.http import HttpResponse
from amcat.model.article import Article
from amcat.model.article import Medium

class SummaryForm(forms.Form):
    start = forms.IntegerField(initial=0, min_value=0, widget=forms.HiddenInput)
    count = forms.IntegerField(initial=30, min_value=1, max_value=10000, widget=forms.HiddenInput)

    
def encode_json_article(obj):
    if type(obj) == list:
        return [encode_json_article(x) for x in obj]
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if isinstance(obj, Medium):
        return "%s - %s" % (obj.id, obj.name)
    if isinstance(obj, Article):
        return "%s - %s" % (obj.id, obj.headline)
    raise TypeError("%r is not JSON serializable" % (obj,))

class ShowSummary(WebScript):
    name = "Summary"
    template = None
    form = SummaryForm
    supportedOutputTypes = ('json-html', 'json')
    
    
    def run(self):
        articles = self.getArticles(start=self.ownForm.cleaned_data['start'], length=self.ownForm.cleaned_data['count'], highlight=True)
        stats = self.getStatistics()
        
        if self.generalForm.cleaned_data['output'] == 'json':
            response = simplejson.dumps({'articles':list(articles), 'statistics':stats.__dict__}, default=encode_json_article)
            return HttpResponse(response, mimetype="application/json")
        else:
            return self.outputArticleSummary(articles, stats)
        
    
    def outputArticleSummary(self, articles, stats=None):
        actions = self.getActions()
        return render_to_string('navigator/selection/articlesummary.html', { 'articles': articles, 'stats':stats, 'actions':actions, 'generalForm':self.generalForm, 'ownForm':self.ownForm})
        