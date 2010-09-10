from cachable import Cachable, DBPropertyFactory, DBFKPropertyFactory, CachingMeta

def parseParams(str):
    """Parse a string:
    
    ontids=1;2;3;4;5;6;7;8;9;10;11;14,language=2
    
    to:
    
    {'ontids' : ['1', '2', '3', '4' ... '14'],
     'language' : ['2']
     }"""
    res = {}
        
    if not str: return res
    
    kargs = str.split(',')
    for k in kargs:
        key, value = k.split('=')
        res[key.strip()] = value.split(';')
    
    return res


class AnnotationSchemaFieldtype(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'annotationschemas_fieldtypes'
    __idcolumn__ = 'fieldtypeid'
    __labelprop__ = 'name'
    
    __dbproperties__ = ("name", "schemafieldid", "fieldeditorid")
    
    schemafield = DBPropertyFactory("schemafieldid", func=lambda x:x[31:])
    fieldeditor = DBPropertyFactory("fieldeditorid", func=lambda x:x[31:])


class AnnotationSchemaField(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'annotationschemas_fields'
    __idcolumn__ = ('annotationschemaid', 'fieldnr')
    __labelprop__ = 'label'
    
    __dbproperties__ = ("fieldnr", "fieldname", "label",
                        "fieldtypeid", "required",
                        "deflt", "section", "values", "table",
                        "keycolumn", "labelcolumn", "sets")
    
    params = DBPropertyFactory("params", func=parseParams)
    fieldtype = DBPropertyFactory("fieldtypeid", dbfunc=AnnotationSchemaFieldtype)
    


class AnnotationSchema(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'annotationschemas'
    __idcolumn__ = 'annotationschemaid'
    __labelprop__ = 'name'
    
    __dbproperties__ = ("description", "articleschema",
                        "languageid", "quasisentences", "sets",
                        "location", "name")
    
    params = DBPropertyFactory("params", func=parseParams)
    schematype = DBPropertyFactory("schematype", func=lambda x: x[35:].split('AnnotationSchema')[0])
    
    def __init__(self, db, id):
        Cachable.__init__(self, db, id)
        
        self.addDBFKProperty('fields',
                             AnnotationSchemaField.__table__,
                             ('annotationschemaid', 'fieldnr'),
                             function=lambda aid, fieldnr: AnnotationSchemaField(db, (aid, fieldnr)),
                             )
        
    #def getLocation(self):
    #    res = {}
    #    
    #    if not self.location: return res
    #    
    #    split = self.location.split(':')
    #    res['table'] = split[0]
    #    res['unique_on'] = split[1:]
    #    
    #    return res
    
    
    
    

if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB()
    asc = AnnotationSchema(db, 24)
    
    print asc.name
    print asc.params
    print asc.schematype
    #print asc.getLocation()
    print asc.fields
    print db
    
    # It's getting escaped properly:
    #asc.update('description', 'bla')
    #db.commit()
    
    print asc.fields[4].fieldtype.fieldeditor