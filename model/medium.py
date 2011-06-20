from django.db import models

from amcat.model.language import Language

class Medium(models.Model):
    id = models.IntegerField(primary_key=True, db_column="medium_id")

    name = models.CharField(max_length=200)
    abbrev = models.CharField(max_length=100)

    circulation = models.IntegerField()
    type = models.IntegerField()

    def __unicode__(self):
        return self.name

    class Meta():
        db_table = 'media'
        app_label = 'model'
    

#class Media(object):
#
#    
#    def clean(self, s):
#        if type(s) == str: s = s.decode("latin-1")
#        return toolkit.clean(s,1,1)
#    def __init__(self, db):
#        self.db = db
#        self.names = {}
#        self.aliasses = {}
#        for medium in Medium.all(self.db):
#            self.names[self.clean(medium.name)] = medium
#    def lookupName(self, name):
#        return self.names.get(self.clean(name))
