import toolkit,article, preprocess, dbtoolkit

aids = list(toolkit.intlist())
db = dbtoolkit.amcatDB()
articles = [article.Article(db, aid) for aid in aids]
print preprocess.splitArticles(articles)
