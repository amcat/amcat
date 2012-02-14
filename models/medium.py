from amcat.tools.model import AmcatModel
from amcat.models.language import Language

from django.db import models

class MediumSourcetype(AmcatModel):
    id = models.AutoField(primary_key=True, db_column="medium_source_id")
    label = models.CharField(max_length=20)

    class Meta():
        db_table = 'media_sourcetypes'

class Medium(AmcatModel):
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column="medium_id")

    name = models.CharField(max_length=200)
    abbrev = models.CharField(max_length=10, null=True, blank=True)
    circulation = models.IntegerField(null=True, blank=True)

    #type = models.ForeignKey(MediumSourcetype, db_column='medium_source_id')
    language = models.ForeignKey("amcat.Language")

    @classmethod
    def get_by_name(cls, name, ignore_case=True):
        """
        Get a medium by label, accounting for MediumAlias.

        @param label: label to look for
        @param ignore_case: use __iexact
        """
        query = dict(name__iexact=name) if ignore_case else dict(name=name)

        try:
            return Medium.objects.get(**query)
        except Medium.DoesNotExist:
            pass

        try:
            return MediumAlias.objects.get(**query).medium
        except MediumAlias.DoesNotExist:
            raise Medium.DoesNotExist("%s could be found in medium nor medium_dict" % name)

    class Meta():
        db_table = 'media'
        verbose_name_plural = 'media'
        app_label = 'amcat'
    
class MediumAlias(AmcatModel):
    """
    Provide multiple names per medium. Please use get_by_name on
    Medium to select a medium.
    """
    __label__ = 'name'

    medium = models.ForeignKey(Medium)
    name = models.CharField(max_length=200)

    class Meta():
        db_table = 'media_alias'
        verbose_name_plural = 'media_aliases'
        app_label = 'amcat'
