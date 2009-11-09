def join(nodea, nodeb, mapping):
    mapping = mapping.parentmapping
    
    indexa = nodea.fields.index(mapping.a)
    indexb = nodeb.fields.index(mapping.b)
    
    reverse = nodea.data is None
    if reverse:
        nodea, nodeb, indexa, indexb = nodeb, nodea, indexb, indexa
    
    newdata = []
    for arow in nodea.data:
        mappedvalues = mapping.map(arow[indexa], reverse=reverse)
        for brow in findrows(nodeb.data, indexb, mappedvalues):
            newdata.append(buildrow(arow, brow, reverse=reverse))

def buildrow(arow, brow, reverse=False):
    if reverse: 
        brow, arow = arow, brow
    return tuple(list(arow) + list(brow))

def findrows(data, index, values):
    if data is None:
        for val in values:
            yield [val]
    else:
        values = set(vales)
        for row in data:
            if row[index] in values:
                yield row  
    
    