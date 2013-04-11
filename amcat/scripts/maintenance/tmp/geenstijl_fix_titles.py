from amcat.models.article import Article
from amcat.scripts.script import Script

def fix_wrong_headlines(self):
    for article in Article.object.filter(
        articlesetarticle__articleset = 66,
        headline__startswith = "#"):


        print(article.headline)
        if article.headline.startswith("#"): #safety measure
            article.headline = article.headline[1:]

        print(article.headline)
