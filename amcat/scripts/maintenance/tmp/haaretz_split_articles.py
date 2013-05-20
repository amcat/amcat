from amcat.models.article import Article
from amcat.models.medium import get_or_create_medium
articles_2025 = Article.objects.filter(articlesetarticle__articleset = 2025)

def run():
    for article in articles_2025:
        m = article.metastring
        if "'_parent'" in m:
            #article is comment
            article.medium = get_or_create_medium("Haaretz - Comments")
        else:
            article.medium = get_or_create_medium("Haaretz")

        print(article.medium)
        #article.save()

if __name__ == "__main__":
    run()
