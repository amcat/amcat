class Type(object):
    def __init__(self, label=None, filters=[], editable=True, cache=True, cellfunc=None, renderer_args={}):
        """
        @label: Label to be shown in tables. This is set to the variable-name by
        tables.__getColumns() if it is not provided here.
        
        @filters: Filters to be applied to the retrieved values.
        
        @editable: Meta-information for Javascript. Whether this column can be edited
        or not.
        
        @cache: If the given objects are cachables, this will enable caching.
        
        """
        self.name = None
        self.label = label        
        self.editable = editable
        self.filters = filters
        self.cache = cache
        self.renderer_args = renderer_args
        self.cellfunc = cellfunc
        
    def __applyFilters(self, val, filters):
        """Apply a number of filters to a lambda function"""
        for fil in filters:
            val = self.__applyFilter(val, fil)
        return val
    
    def __applyFilter(self, val, filter):
        """Apply a filter to a lambda function"""
        return lambda x: filter(val(x))
            
    @property    
    def filter(self):
        """Return a filtered 'self'."""
        if self.cellfunc:
            val = self.cellfunc
        else:
            val = lambda x:getattr(x, self.name)
            
        return self.__applyFilters(val, self.filters)
    
    def getLabel(self):
        return self.label

class Integer(Type):
    pass
        
class String(Type):
    pass

class Email(Type):
    pass

class List(Type):
    pass

class Dictionary(Type):
    pass

class Html(Type):
    """Same as String, but values will not be escaped
    by AmCAT"""
    pass

class Boolean(Type):
    def getLabel(self):
        return '%s?' % self.label

class Choice(Type):
    def __init__(self, choices, *arg, **kargs):
        super(Choice, self).__init__(renderer_args={'options' : choices}, *arg, **kargs)
        


if __name__ == '__main__':
    x = Choice({1 : 'ok'},
               label='One choice',
               editable=False)
    
    print x.label
    print x.choices
    print x.editable