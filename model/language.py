from django.db import models

class Language(models.Model):    
    id = models.IntegerField(primary_key=True, db_column="language_id")
    label = models.CharField(max_length=200)

    class Meta():
        db_table = 'languages'
        app_label = 'model'
