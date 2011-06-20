from django import db

from amcat.model import article

a = article.Article.objects.get(id=57220255)

print(a.headline)
print(a.date)
print(repr(a.medium))
print(a.medium.id)
print(a.sentences.all())
print(repr(a.project))
