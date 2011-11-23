from amcat.tools import toolkit

from amcat.tools.table.table3 import ObjectColumn

import logging; log = logging.getLogger(__name__)

class FieldColumn(ObjectColumn):
    """ObjectColumn based on a AnnotationSchemaField"""
    def __init__(self, field, article=None, fieldname=None, label=None, fieldtype=None):
        if fieldtype is None: fieldtype = field.getTargetType()
        if article is None: article = field.schema.isarticleschema
        if fieldname is None: fieldname = field.fieldname
        if label is None: label = field.label
        ObjectColumn.__init__(self, label, fieldname, fieldtype=fieldtype)
        self.field = field
        self.article = article
        self.valuelabels = {}
    def getUnit(self, row):
        return row.ca if self.article else row.cs
    def getCell(self, row):
        try:
            val = self.getValue(row)
            return val
        except AttributeError, e:
            log.debug("AttributeError on getting %s.%s: %s" % (row, self.field, e))
            raise
            return None
    def getValues(self, row):
        unit = self.getUnit(row)
        if unit is None: return None
        values = unit.values
        return values
        
    def getValue(self, row, fieldname = None):
        if not fieldname: fieldname = self.field.fieldname
        log.debug(">>>>>> getValue(%r, %r)" % (row, fieldname))
        values = self.getValues(row)
        if values is None: return None
        try:
            val = getattr(values, fieldname)
        except AttributeError:
            log.error("%r has no field %r, but it has %r" % (values, fieldname, dir(values)))
            raise
        log.debug(">>>>>> values=%r, fieldname=%r, --> val=%s" % (values, fieldname, val))
        return val
