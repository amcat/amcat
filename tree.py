import string

class Node:
  def __init__(this, tree, name):
    this.tree      = tree
    this.name      = name 
    this.rel       = 1
    this.parent    = None #backref
    this.children  = []
    this.info      = None

    this.tree.index[name] = this


  def visualize(this, tab = ""):
    res = ""
    nt = "\t" + tab
    for s in this.children:
      res += "%s%s\n" % (tab,s)
      res += s.visualize(nt)
    return res

  def getChildren(this, relp=1):
    res = []
    for node in this.children:
      rel = node.rel * relp
      res.append((node, rel))
      res += node.getChildren(rel)
    return res


  def setdepth(this, depth):
    this.depth = depth
    if depth > this.tree.maxdepth:
      this.tree.maxdepth = depth
    
    for child in this.children:
      child.setdepth(depth+1)
      

  def __str__(this):
    return "%s [%s]" % (this.name, this.rel)

class Tree(Node):

  def __init__(this, lines):
    this.index = {}
    this.maxdepth = 0

    Node.__init__(this, this, "<ROOT>")

    if lines:
      this.read(lines)

  def getdepth(this, name):
    if name in this.index:
      return this.index[name].depth
    else:
      return -1
    
  def read(this, lines):
    
    for line in lines:
      if line.strip():
        i = map(string.strip, line.strip().split('|', 3))
        o,s,r = i[:3]
        if len(i) > 3:
          info = i[3]
        else:
          info =None

        if not s:
          sNode = this
        elif s in this.index:
          sNode = this.index[s]
        else:
          sNode = Node(this, s)
          this.index[s] = sNode

        if o in this.index:
          oNode = this.index[o]
        else:
          oNode = Node(this, o)

        oNode.parent = sNode
        oNode.rel    = int(r)
        oNode.info   = info

        sNode.children.append(oNode)

    #determine depths
    this.setdepth(0)
    
if __name__ == '__main__':
  import sys
  t = Tree(sys.stdin)
  t.visualize()
