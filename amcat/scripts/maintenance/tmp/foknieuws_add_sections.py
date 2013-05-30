from amcat.models.article import Article

fok_articles = Article.objects.filter(medium=989899008)
n_articles = fok_articles.count()
i = 0
for article in fok_articles:
    i+= 1
    if article.url:
        article.section = article.url.split("/")[3]
    
    print("{i}/{n_articles}: {article.section} : {article}".format(**locals()))
    article.save()
