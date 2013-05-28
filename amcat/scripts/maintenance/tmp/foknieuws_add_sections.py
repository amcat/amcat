from amcat.models.article import Article

fok_articles = Article.objects.filter(medium=989899008)
n_articles = fok_articles.count()
for i,article in enumerate(articles):
    article.section = article.url.split("/")[3]
    print("{i}/{n_articles}: {article.section} : {article}".format(**locals()))
    #article.save()
