from django import db
from django.db import connection

from pprint import pprint

from amcat.model import article
from amcat.model import project
from amcat.model import user
from amcat.model import authorisation

#print('Initialized!\n')

a = article.Article.objects.get(id=57220255)

print('Article ID:\t\t' + str(a.id))
print('Headline:\t\t' + a.headline)
print('Date:\t\t\t' + str(a.date))
print('Medium:\t\t\t' + repr(a.medium))
print('Medium ID:\t\t' + str(a.medium.id))
print('Sentence 1:\t\t' + repr(a.sentences.all()[0]))
print('Sentence 2:\t\t' + repr(a.sentences.all()[1]))
print('Sentence 5:\t\t' + repr(a.sentences.all()[4]))
print('Project:\t\t' + repr(a.project))
print('Project insert user:\t' + repr(a.project.insert_user))

u = user.User.objects.get(id=2)
print('\nUser:\t\t\t' + repr(u))
print('Projects:\t\t' + repr(u.projects.all()))
print('Roles:\t\t\t' + repr(u.roles.all()))
print('Project roles:\t\t' + repr(u.p_roles.all()))

p = project.Project.objects.get(id=2)
print('\nProject:\t\t' + repr(p))
print('Users:\t\t\t' + repr(p.user_set.all()))

r = authorisation.Role.objects.get(id=1)
print('\nRole:\t\t\t' + repr(r))
print('Users:\t\t\t' + repr(r.user_set.all()))


#for c in connection.queries:
#    print(c)
