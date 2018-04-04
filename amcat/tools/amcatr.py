"""
Useful functions for interfacing with R
"""

from rpy2 import robjects, rinterface
from rpy2.rlike.container import OrdDict
import datetime

def to_r(values):
    """
    Convert primitive python value(s) into an R vector

    values should be a object or tuple/list of a primitive type (bool, int, str)
    If values is already an R vector, it is returned unmodified
    """
    if isinstance(values, rinterface.SexpVector):
        return values
    if not isinstance(values, (tuple, list)):
        values = [values]
    val = next((x for x in values if x is not None), None)
    if isinstance(val, bool):
        vtype, natype = robjects.BoolVector, rinterface.NA_Integer        
    elif isinstance(val, int) or (val is None):
        vtype, natype = robjects.IntVector, rinterface.NA_Integer
    elif isinstance(val, str):
        vtype, natype = robjects.StrVector, rinterface.NA_Character
    elif isinstance(val, float):
        vtype, natype = robjects.FloatVector, rinterface.NA_Real
    elif isinstance(val, datetime.datetime):
        # sorry, I don't know how to do NA_Posixct, so doing this the ugly way
        nas = [i for (i,x) in enumerate(values) if x is None]
        values = [datetime.datetime(1900,1,1) if x is None else x for x in values]
        result = robjects.POSIXct(values)
        for na in nas:
            result[na] = robjects.NA_Real
        return result
    else:
        raise TypeError("Don't know how to convert {} to R".format(type(val)))

    values = [natype if x is None else x for x in values]
    return vtype(values)
    

def create_dataframe(columns):
    """
    Create a data frame from [(name, values), ..] columns (e.g. from a dict.iteritems())
    """
    result = OrdDict()
    for name, values in columns:
        result[name] = to_r(values)
    return robjects.DataFrame(result)

def save(filename, **objects):
    """Save one or more R objects as .rda file"""
    for name, val in objects.items():
        robjects.rinterface.globalenv[str(name)]=to_r(val)
    robjects.r.save(file=filename, *objects.keys())

def save_to_bytes(**objects):
    """Save R objects to an .rda, returned as bytes (i.e. in-memory)"""
    import os, tempfile
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile() as f:
        save(f.name, **objects)
        result = f.read()
    return result
    
