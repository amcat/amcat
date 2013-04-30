from amcat.models.article import Article

def fix_wrong_headlines():
    for article in Article.objects.filter(
        articlesetarticle__articleset = 66,
        headline__startswith = "#"):


        if article.headline.startswith("#"): #safety measure
            article.headline = article.headline[1:].strip()

        article.save()

if __name__ == "__main__":
    fix_wrong_headlines()
