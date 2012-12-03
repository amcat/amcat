"""This script is meant for one time use, removing all index pages from scraped articlesets."""


from amcat.models.article import Article
from amcat.models.articleset import ArticleSetArticle
from amcat.models.scraper import Scraper

scrapers = Scraper.objects.all()

articles = Article.objects.filter(
    articlesetarticle__articleset__in = [s.articleset_id for s in scrapers]
    )


def check_for_ipage(article):
    if article.headline.startswith("[INDEX]"):
        return True
    else:
        return False


def remove_article(article):
    ArticleSetArticle.objects.filter(article = article).delete()
    article.delete()

for article in articles:
    if check_for_ipage(article):
        remove_article(article)


 

    
