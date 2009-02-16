import exceptions, toolkit

class DuplicateNameException(exceptions.Exception): pass
class DuplicateValueException(exceptions.Exception): pass

class Enum(object):
    def __init__(self, *values, **valdict):
        self.lookup = {}
        self.reverseLookup = {}
        self.labels = {}
        self.values = []
        if len(values) == 1 and toolkit.isIterable(values[0], True):
            values = values[0]
        for x in values:
            if isinstance(x, EnumValue):
                x.enum = self
                if x.value is None: x.value = len(self.values)
                self.add(x)
            else:
                self.add(EnumValue(x, value=len(self.lookup), enum=self))
        for x, v in sorted(valdict.items()):
            if type(v) in (int, long):
                self.add(EnumValue(x, value=v, enum=self))
            else:
                self.add(EnumValue(x, value=len(self.lookup), label=v, enum=self))

    def add(self, value):
        if value.name in self.lookup: raise DuplicateNameException(value.name)
        if value.value in self.reverseLookup: raise DuplicateValueException(value.value)
        self.values.append(value)
        self.lookup[value.name] = value
        self.reverseLookup[value.value] = value
        
    def __getattr__(self, attr):
        if not self.lookup.has_key(attr):
            print self.lookup
            raise AttributeError
        return self.lookup[attr]
    
    def fromValue(self, value):
        return self.reverseLookup[value]

    def fromName(self, name):
        return self.lookup[name]

    def get(self, obj):
        if isinstance(obj, EnumValue) and obj.enum == self: return obj
        if obj in self.lookup: return self.lookup[obj]
        if obj in self.reverseLookup: return self.reverseLookup[obj]
        raise KeyError(obj)

    def getNames(self):
        return [val.name for val in self.values]

class EnumValue(object):
    def __init__(self, name, label=None, value=None, enum=None, data={}):
        if not label: label = name
        self.enum = enum
        self.name = name
        self.value = value
        self.label = label
        self.data = data
    def __str__(self):
        return self.label
    def __repr__(self):
        return "EnumValue(%r, %r, %r)" % (self.name, self.value, self.label)
if __name__ == '__main__':
    x = Enum(["red","green","blue"])
    print x.red
    print x.getName(2)
    print x.getValue("green")

    x = Enum("red","green","blue")
    print x.red
    print x.getName(2)
    print x.getValue("green")

    x = Enum(red="The Red Option", green="Bla",blue="The Blue Option")
    print x.red
    print x.getName(2)
    print x.getValue("green")

    x = Enum(EnumValue("red", 0, "The Red Option"),
             EnumValue("green", 1, "The Green Option"),
             EnumValue("blue", 2, "The Blue Option"),
             )
             
    print x.red.value, x.red
    print x.getName(2).value, x.getName(2)
    print x.getValue("green").value, x.getValue("green")
    
    
