from amcat.tools import toolkit, idlabel
import logging; log = logging.getLogger(__name__)
import datetime
from amcat.tools.table.table3 import ObjectColumn
from amcat.model.coding import codingjob, annotationschema
from amcat.scripts.export_codingjobresults import FieldColumn
from amcat.model.ontology.hierarchy import BoundObject
from amcat.model.ontology.object import Object
from amcat.model.ontology.tree import Tree

from amcat.tools.logging import amcatlogging ;amcatlogging.debugModule()

from sentencetypes import SENTENCE_TYPES_FINE,  SENTENCE_TYPES_COARSE, SUPPORT_CRITICISM_INTERNAL, SUPPORT_CRITICISM, IDEAL, MEDIA

CODEBOOK_CACHE = {}
def getCodebook(codebook):
    if codebook.id not in CODEBOOK_CACHE:
        CODEBOOK_CACHE[codebook.id] = codebook
    return CODEBOOK_CACHE[codebook.id]

DIM_TREE = None
def getDimTree(db):
    global DIM_TREE
    if DIM_TREE is None:
        DIM_TREE = Tree(db, 5001)
    return DIM_TREE


def _doExtrapolate(values):
    d = values._asdict()
    d["object"],  d["subject"], d["source"] = d["subject"],  d["source"], None
    if not d["subject"]:
	d["subject"] = Object(d["object"].db, MEDIA)
    values = type(values)(**d) # clone
    return values

class NetColumn(FieldColumn):
    def __init__(self, field, label):
        FieldColumn.__init__(self, field)
        self.label = field.fieldname + label
        self.fieldname += label
	self.codebook = getCodebook(self.field.serializer.codebook)
	self.extrapolate = True
    def getValues(self, row):
	values = super(NetColumn, self).getValues(row)
	if values is None or not self.extrapolate: return
	
	src, su, obj = [getattr(values, x) for x in  ("source","subject","object")]
	objtype = self.codebook.categorise(obj, date=row.art.date, depth=1)[-1]
	if objtype.id == IDEAL:
	    values = _doExtrapolate(values)
	return values
	
    def getCell(self, row):
        val = super(NetColumn, self).getCell(row)
        if val is None: return
        if not issubclass(self.field.getTargetType(), Object):
            return val
        val = self.codebook.getObject(val)
        val = self._getCell(val, row)
        if isinstance(val, BoundObject):
            val = val.objekt
        if val: return val
    def _getCell(self, obj):
        """Return the val for this BoundObject (bound to self.codebook)"""
        raise NotImplementedError

class CategorisationColumn(NetColumn):
    def __init__(self, field, label, depth):
        NetColumn.__init__(self, field, label)
        self.depth = depth
    def _getCell(self, obj, row):
        return self.codebook.categorise(obj, date=row.art.date, depth=self.depth)[-1]

class OmklapColumn(NetColumn):
    def __init__(self, field, label, depth=2):
        NetColumn.__init__(self, field, label)
        self.depth = depth
    def _getCell(self, obj, row):
        return self.codebook.categorise(obj, date=row.art.date, depth=self.depth, returnReverse=True, returnObject=False)[-1]


class DimensionColumn(CategorisationColumn):
    def __init__(self, field, label):
        CategorisationColumn.__init__(self, field, label, depth=3)
        self.dimtree = getDimTree(self.codebook.db)
    def _getCell(self, obj, row):
        val = super(DimensionColumn, self)._getCell(obj, row)
        if not val: return
        return self.dimtree.getParent(val)

class InstitutionColumn(NetColumn):
    def __init__(self, field, label, functionid=False, party=False):
        NetColumn.__init__(self, field, label)
        self.functionid = functionid
        self.party = party
    def _getCell(self, obj, row):
        functions = list(obj.objekt.currentFunctions(date=row.art.date, party=self.party))
        if functions:
            function = toolkit.head(functions)
            if self.functionid: return function.functionid
            else: return function.office

class PartyTypeColumn(InstitutionColumn):
    def __init__(self, field, label):
        InstitutionColumn.__init__(self, field, label, functionid=False, party=True)
    def _getCell(self, obj, row):
        party = super(PartyTypeColumn, self)._getCell(obj, row)
        if party: return getPartyType(party, row.art.date)

class SentenceTypeColumn(ObjectColumn):
    def __init__(self, label, schema, dictionary, internal):
        ObjectColumn.__init__(self, label, fieldtype=idlabel.IDLabel)
	self.schema = schema
	su = schema.getField("subject")
	obj = schema.getField("object")
	self.sutype = CategorisationColumn(su, "x", 1)
	self.objtype = CategorisationColumn(obj, "x", 1)
	self.suroot = CategorisationColumn(su, "x", 2)
	self.objroot = CategorisationColumn(obj, "x", 2)
        self.dictionary = dictionary
        self.internal= internal
    def getCell(self, row):
	su = self.sutype.getCell(row)
        obj = self.objtype.getCell(row)
        if su and obj:
            result = self.dictionary.get((su.id, obj.id))
            if self.internal and result == SUPPORT_CRITICISM:
                sucat = self.suroot.getCell(row)
                objcat = self.objroot.getCell(row)
                if sucat == objcat:
                    result = SUPPORT_CRITICISM_INTERNAL
            return result

COALITIE_OID = 2695
OPPOSITIE_OID = 1753

def getPartyType(party, date):
    functions = sorted(party.functions, key = lambda f: f.fromdate)
    functions = filter(lambda f : f.fromdate <= date, functions)
    if not functions: return idlabel.IDLabel(3, "New")
    if functions[-1].office.id == COALITIE_OID:
	return idlabel.IDLabel(1, "Coalition")
    if any(f.office.id == COALITIE_OID for f in functions):
	return idlabel.IDLabel(2, "Opposition")
    if functions[0].fromdate > date - datetime.timedelta(days=365 * 3):
	return idlabel.IDLabel(3, "New")
    return idlabel.IDLabel(4, "Structural Opposition")
        
COLUMNS = [
     lambda field : CategorisationColumn(field, "class", 1),
     lambda field : CategorisationColumn(field, "root", 2),
     lambda field : CategorisationColumn(field, "cat", 3),
     lambda field : DimensionColumn(field, "dim"),
     lambda field : InstitutionColumn(field, "inst"),
     lambda field : InstitutionColumn(field, "func", functionid=True),
     lambda field : InstitutionColumn(field, "partyleader", functionid=True, party=True),
     lambda field : PartyTypeColumn(field, "partytype"),
     ]

def getColumnsForField(field):
    if issubclass(field.getTargetType(), Object):
        return getColumnsForObjectField(field)
    elif field.fieldname == 'quality':
        return [AggrQualColumn(field)]
    return []

def getColumnsForObjectField(field):
    return (c(field) for c in COLUMNS)

def getArrowColumns(schema):
    return [
        SentenceTypeColumn("sentencetypedetail", schema, SENTENCE_TYPES_FINE, True),
        SentenceTypeColumn("sentencetype", schema,  SENTENCE_TYPES_COARSE, False),
        ]

class AggrQualColumn(FieldColumn):
    def __init__(self, field, label='aggrqual'):
        FieldColumn.__init__(self, field, fieldname=label, label=label)
	su = self.field.schema.getField("subject")
	obj = self.field.schema.getField("object")
	self.surootcol = OmklapColumn(su, "x", 2)
	self.objrootcol = OmklapColumn(obj, "x", 2)

    def getCell(self, row):
        val = super(self.__class__, self).getCell(row)
        if val is None: return
	for col in self.surootcol, self.objrootcol:
            omklap = col.getCell(row)
            if omklap: val *= -1
        return val

if __name__ == '__main__':
    from amcat.db import dbtoolkit
    from amcat.model.ontology.object import Object
    db = dbtoolkit.amcatDB()

    for date in '2002-01-01', '2003-01-01', '2008-01-01', '2010-08-01', '2011-01-01':
        date = toolkit.readDate(date)
        print "-----",str(date)[:10],"-----"
        partijen = ['vvd','sp','pvv','lpf, lijst vijf fortuyn','d66','cda']

        for partij in partijen:
            ids = db.doQuery("select distinct objectid from o_labels where label = '%s'" % partij.replace("'","''"))
            if len(ids) != 1:
                raise Exception([partij, ids])
            partij = Object(db, ids[0][0])
            #print "---", partij
            type = getPartyType(partij, date)
	    print partij, type
