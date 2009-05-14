import ontology, user, article, exceptions

class AdapterException(exceptions.Exception):pass

def getLink(obj, strict=False):
    if obj is None: return None
    try:
        return obj.getLink()
    except AttributeError: pass
    if strict: raise AdapterException("Cannot get link for %s" % obj)

def getLabel(obj, strict=False):
    if obj is None: return None
    if type(obj) in (str, float, int): return str(obj)
    if type(obj) == user.User: return obj.username
    if type(obj) == article.Article: return obj.headline
    try:
        return obj.getLabel()
    except AttributeError, e: pass
    for x in "label", "name":
        try:
            return obj.__getattribute__(x)
        except AttributeError, e:
            try:
                return obj.__getattr__(x)
            except AttributeError, e:
                pass
    if strict: raise AdapterException("Cannot get label for %s" % obj)

def getID(obj, strict=False, default=None):
    if obj is None: return None
    if isinstance(obj, ontology.Node):
        return obj.getNr()
    try: return obj.__id__()
    except AttributeError: pass
    try: return obj.id
    except AttributeError: pass
    if default: return default
    if strict: raise AdapterException("Cannot get ID for %s, type=%s" % (obj, type(obj)))
    
    
