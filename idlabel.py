import logging; log = logging.getLogger(__name__)

class Identity(object):
    """
    Simple class representing an object which can be compared to
    other Identity objects based on an identity() function
    """
    def __init__(self, *identity):
        self.__identity__ = tuple([self.__class__] + list(identity)) if identity else None
    def identity(self):
        if self.__identity__ is None: raise Exception("Identity object without identity")
        return self.__identity__
    def __repr__(self):
        try:
            i = self.identity()
            if i[0] == self.__class__: i = i[1:]
            return "%s%r" % (type(self).__name__, i)
        except Exception, e:
            import traceback; traceback.print_exc()
            return "#ERROR on __repr__: %s" % e
    def __str__(self):
        return repr(self)
    def __hash__(self):
        return hash(self.identity())
    def __eq__(self, other):
        if other is None: return False
        if not isinstance(other, Identity): return False
        return self.identity() == other.identity()
    def __cmp__(self, other):
        if not isinstance(other, Identity): return -1
        return cmp(self.identity(), other.identity())

class IDLabel(Identity):
    """
    Simple class representing objects with a label and ID. Identity checks equality
    on class + ID; str( ) returns the label, repr( ) return class(id, label, ..)
    """
    def __init__(self, id, label=None):
        Identity.__init__(self, self.__class__, id)
        self.id = id
        self._label = label

    @property
    def label(self):
        if self._label is None:
            log.warn("%r has no label" % self)
            return repr(self)
        return self._label
        
    def identity(self):
        return (self.__class__, self.id)
    def clsidlabel(self):
        return "%s %s" % (type(self).__name__, self.idlabel())
    def idlabel(self):
        return "%s: %s" % (self.id, self.label)
    def __str__(self):
        try:
            if type(self.label) == unicode:
                return self.label.encode('ascii', 'replace')
            else:
                return str(self.label)
        except AttributeError:
            return repr(self)
    def __unicode__(self):
        try:
            if type(self.label) == unicode:
                return self.label
            else:
                return str(self.label).decode('latin-1')
        except AttributeError:
            return unicode(repr(self))
        
    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, self.id)
