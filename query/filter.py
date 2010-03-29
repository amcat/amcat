import toolkit

class Filter(object):
    def __init__(self, concept):
        self.concept = concept
    def getValues(self):
        return None
    def getSQL(self, fieldname):
        abstract

class ValuesFilter(Filter):
    def __init__(self, concept, *values):
        Filter.__init__(self, concept)
        self.values = tuple(concept.getObject(value) for value in values)
    def getValues(self):
        return self.values
    def __str__(self):
        return "%s in (%s)" % (self.concept, ",".join(map(str, self.values)))

class IntervalFilter(Filter):
    def __init__(self, concept, fromValue=None, toValue=None):
        Filter.__init__(self, concept)
        self.fromValue = fromValue
        self.toValue = toValue
    def getSQL(self, fieldname):
        fromsql = toolkit.quotesql(self.fromValue)
        tosql = toolkit.quotesql(self.toValue)
        if self.fromValue and self.toValue:
            return "%s BETWEEN %s AND %s" % (fieldname, fromsql, tosql)
        else:
            if self.fromValue:
                op, val = ">", fromsql
            else:
                op, val = "<", tosql
            return "%s %s %s" % (fieldname, op, val)
    def __str__(self):
        if self.fromValue and self.toValue:
            return "%s in (%s..%s)" % (self.concept, self.fromValue, self.toValue)
        elif self.fromValue:
            return "%s > %s" % (self.concept, self.fromValue)
        else:
            return "%s < %s" % (self.concept, self.toValue)
