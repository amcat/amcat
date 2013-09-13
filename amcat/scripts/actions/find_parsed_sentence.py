from amcat.models import AnalysedArticle, Token, ArticleSet, Plugin
from amcat.scripts.script import Script
from django import forms
from django.db.models import Q
import operator
import csv, sys


class FindParsedSentence(Script):

    """
    Find a sentence in a given set that has been parsed with the specified plugin
    and contains specific word(s). Useful for testing grammar rules
    """
    
    class options_form(forms.Form):
        articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
        plugin = forms.ModelChoiceField(queryset=Plugin.objects.all())
        words = forms.CharField(help_text="Multiple words can be specified separated by space, remember to put the argument in quotes")


        
    def _run(self, articleset, plugin, words):
        arts = AnalysedArticle.objects.filter(article__articlesets_set=articleset, plugin_id=plugin, done=True)

        # create lemma filter from |'d Q objects using reduce
        qs = reduce(operator.or_, map(get_q, words.split(" ")))

        w = csv.writer(sys.stdout)
        w.writerow(['aid', 'sid', 'asid', 'word', 'sentence'])

        
        for art in arts:
            seen = set()
            for token in Token.objects.filter(sentence__analysed_article=art).filter(qs):
                if token.sentence in seen: continue
                seen.add(token.sentence)
                
                w.writerow([token.sentence.analysed_article.article_id,
                            token.sentence.analysed_article.id,
                            token.sentence.id,
                            token,
                            token.sentence.sentence])
                

        
def get_q(word):
    return Q(word__lemma__lemma=word)
        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()
    #print result.output()

