from amcat.tools import toolkit

from amcat.tools.model import AmcatModel
from amcat.model.project import Project

from django.db import models

import logging; log = logging.getLogger(__name__)


class ValidationError(ValueError):
    pass

class RequiredValueError(ValidationError):
    pass

class AnnotationSchema(AmcatModel):
    id = models.IntegerField(db_column='annotationschema_id', primary_key=True)

    name = models.CharField(max_length=75)
    description = models.TextField()

    isnet = models.BooleanField()
    isarticleschema = models.BooleanField()
    quasisentences = models.BooleanField()

    project = models.ForeignKey(Project)
    
    def __unicode__(self):
        return "%s - %s" % (self.id, self.name)

    class Meta():
        db_table = 'annotationschemas'
        app_label = 'amcat'

    def asDict(self, values):
        return dict(zip([f.fieldname for f in self.fields], values))

    def validate(self, values):
        """Validate whether the given values are a valid coding for this schema
        raises a VAlidationError if not, returns silenty if ok.

        @param values: Dict of {schemafield : (deserialized) values}
        """
        for field in self.fields:
            field.validate(values.get(field))

    def deserializeValues(self, **values):
        """Deserialize a {fieldname:valuestr} dict to a {field:value} dict"""
        objects = {}
        for (k,v) in values.items():
            f = self.getField(k)
            o = f.deserialize(v)
            objects[f] = o
        return objects

