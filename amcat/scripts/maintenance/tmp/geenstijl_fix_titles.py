from amcat.models.article import Article

def fix_wrong_headlines():
    for article in Article.object.filter(
        articlesetarticle__articleset = 66,
        headline__startswith = "#"):


        print(article.headline)
        if article.headline.startswith("#"): #safety measure
            article.headline = article.headline[1:]

        print(article.headline)


if __name__ == "__main__":
    fix_wrong_headlines()
