from amcat.tools.model import AmcatModel
from amcat.model.language import Language

from django.db import models

class MediumSourcetype(AmcatModel):
    id = models.AutoField(primary_key=True, db_column="medium_source_id")
    label = models.CharField(max_length=20)

    class Meta():
        db_table = 'media_sourcetypes'

class Medium(AmcatModel):
    id = models.AutoField(primary_key=True, db_column="medium_id")

    name = models.CharField(max_length=200)
    abbrev = models.CharField(max_length=10, null=True)
    circulation = models.IntegerField(null=True)

    #type = models.ForeignKey(MediumSourcetype, db_column='medium_source_id')
    language = models.ForeignKey("amcat.Language")

    def __unicode__(self):
        return self.name

    class Meta():
        db_table = 'media'
        verbose_name_plural = 'media'
        app_label = 'amcat'
    

