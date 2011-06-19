from django.db import models

class Language(models.Model):    
    languageid = models.IntegerField(primary_key=True)
    label = models.CharField(max_length=200)

    class Meta():
        db_table = 'languages'

    
