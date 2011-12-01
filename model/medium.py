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

    @classmethod
    def get_by_name(cls, name, ignore_case=True):
        """
        Get a medium by label, accounting for MediumDict.

        @param label: label to look for
        @param ignore_case: use __iexact
        """
        query = dict(name__iexact=name) if ignore_case else dict(name=name)

        try:
            return Medium.objects.get(**query)
        except Medium.DoesNotExist:
            pass

        try:
            return MediumDict.objects.get(**query).medium
        except MediumDict.DoesNotExist:
            raise Medium.DoesNotExist("%s could be found in medium nor medium_dict" % name)

    def __unicode__(self):
        return self.name

    class Meta():
        db_table = 'media'
        verbose_name_plural = 'media'
        app_label = 'amcat'
    
class MediumDict(AmcatModel):
    """
    Provide multiple names names per medium. Please use get_by_name on
    Medium to select a medium.
    """
    medium = models.ForeignKey(Medium)
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name

    class Meta():
        db_table = 'media_dict'
        verbose_name_plural = 'media_dicts'
        app_label = 'amcat'
