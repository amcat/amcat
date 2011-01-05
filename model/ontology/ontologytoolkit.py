import logging; log = logging.getLogger(__name__)


def getParent(obj, db, oid, pid):
    """@param obj: constructor argument.
    @type obj: model-object
 
    @param oid: objectid (see table `hierarchy`)
    @param pid: parentid ("")

    @return: Tree, Object or Tree, None when requested
    object is a direct child of `Tree`.
    """
    from amcat.model.ontology.object import Object
    from amcat.model.ontology.tree import Tree

    tree = Tree(db, oid)
    if pid is None:
        return tree, None
    return tree, Object(db, pid)

def getAllAncestors(object, stoplist=None, golist=None):
    if stoplist is None: stoplist = set()
    for p in object.getAllParents():
        if (p is None) or (p in stoplist): continue
        if (golist and p not in golist): continue
        yield p
        stoplist.add(p)
        for o2 in getAllAncestors(p, stoplist, golist):
            yield o2

def getAllDescendants(object, stoplist=None, golist=None):
    if stoplist is None: stoplist = set()
    children = object.children
    if not children: return
    for p in children:
        if (p is None) or (p in stoplist): continue
        if (golist and p not in golist): continue
        yield p
        stoplist.add(p)
        for o2 in getAllDescendants(p, stoplist, golist):
            yield o2

def function2conds(function):
    officeid = function.office.id
    if officeid in (380, 707, 729, 1146, 1536, 1924, 2054, 2405, 2411, 2554, 2643):
        if function.functionid == 2:
            return ["bewinds*", "minister*"]
        else:
            return ["bewinds*", "staatssecret*"]

    if officeid == 901:
        return ["premier", '"minister president"']
    if officeid == 548:
        return ["senator", '"eerste kamer*"']
    if officeid == 1608:
        return ["parlement*", '"tweede kamer*"']
    if officeid == 2087:
        return ['"europ* parlement*"', "europarle*"]
    return []
