from amcat.models.article import Article
from amcat.models.medium import get_or_create_medium
articles_2025 = Article.objects.filter(articlesetarticle__articleset = 2025)

def run():
    i = 0
    while True:
        article = articles_2025[i]
        i += 1
        m = article.metastring
        print(m)
        if m and "'_parent'" in m:
            #article is comment
            article.medium = get_or_create_medium("Haaretz - Comments")
        else:
            article.medium = get_or_create_medium("Haaretz")

        print(article.medium)
        #article.save()

if __name__ == "__main__":
    run()
