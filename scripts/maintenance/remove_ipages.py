"""This script is meant for one time use, removing all index pages from scraped articlesets."""


from amcat.models.article import Article
from amcat.models.articleset import ArticleSetArticle
from amcat.models.scraper import Scraper
from amcat.models.project import Project

trashbin = Project.objects.get(pk=2)

scrapers = Scraper.objects.all()




def check_for_ipage(article):
    if article.headline.startswith("[INDEX]"):
        return True
    else:
        return False


def remove_article(article):
    ArticleSetArticle.objects.filter(article = article).delete()
    article.project = trashbin
    article.save()



#per scraper only takes too much memory
def days():
    from datetime import date, timedelta
    date = date(2012, 01, 01)
    while date <= date.today():
        yield date
        date += timedelta(days=1)


def run():
    for scraper in scrapers:
        print(scraper)
        for day in days():
            print(day)
            articles = Article.objects.filter(
                articlesetarticle__articleset = scraper.articleset_id,
                date__contains = day
                )
            print(len(articles))
            for article in articles:
                if check_for_ipage(article):
                    print("removing {}".format(article))
                    remove_article(article)



 

if __name__ == "__main__":
    run()
    
