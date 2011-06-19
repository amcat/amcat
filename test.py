from django import db

from amcat.model import article

a = article.Article.objects.get(articleid=57356278)

print(a.headline)
print(a.date)
print(repr(a.medium))
print(a.medium.mediumid)
print(a.sentences.all())
