from amcat.models.medium import Medium
from amcat.models.article import Article
from amcat.scripts.article_upload.bzk_aliases import BZK_ALIASES as aliases

for alias, medium in aliases.items():
    if alias != medium:
        print(alias, " > ", medium)
    #change all articles in project 29
        alias = Medium.get_or_create(alias)
        articles = Article.objects.filter(medium = alias.id, project_id = 29)
        print("{} articles".format(articles.count()))
        articles.update(medium = Medium.get_or_create(medium).id)
    #if medium is now empty, delete
        if Article.objects.filter(medium = alias.id).count() == 0:
            print('deleting...')
            alias.delete()
    else:
        print('alias is no alias')

