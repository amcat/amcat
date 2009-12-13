import collections, toolkit, datasource

def profile(s):
    toolkit.ticker.warn(s)
 
class State(toolkit.Identity):
    def __init__(self, edges=None, cost=0):
        self.edges = set(edges) or set()
        self.cost = cost
    def identity(self):
        return tuple(sorted(self.edges))
    def __str__(self):
        return "State([%s], %i)" % (",".join(map(str, self.edges)), self.cost)
    def getEdges(self):
        return self.edges
    def getNodes(self):
        return getNodes(self.edges)
    def isSolution(self, goal):
        return not (set(goal) - self.getNodes())
    def appendToState(self, edge):
        return State(self.edges | set([edge]), self.cost + edge.getCost())
    __repr__ = __str__

def getNodes(edges):
    s = set()
    for edge in edges:
        s |= set(edge.getNodes())
    return s

def getNeighbours(edges):
    "Returns a dict of concept : edges)"
    neighbours = collections.defaultdict(set)
    for edge in edges:
        for node in edge.getNodes():
            neighbours[node].add(edge)
    return neighbours
    
class StartEdge(toolkit.Identity):
    def __init__(self, node):
        self.node = node
    def identity(self):
        return self.node
    def getNodes(self): return [self.node]
    def getCost(self): return 0
    def __str__(self): return str(self.node)

    
def getSolution(edges, goal):
    """
    Computes the Minimal Spanning Tree for the edges that contains all nodes in goal
    edges : collection of objects implementing IEdge:
              getNodes()
              getCost()
    goal : collection of nodes (comparable using == to the result of the getNodes() of the edges)
    """
    neighbours = getNeighbours(edges)
    # print "neighbours:"
    # for a, bs in neighbours.items():
    #     print "  %s : [%s]" % (a, ",".join(map(str, bs)))
    states = []
    for g in goal:
        states.append(State([StartEdge(g)], 0))
        break
    solution = None # best state so far
    i = 0
    while True:
        i += 1
        profile("Iteration %i, #states %i, solutions? %s" % (i, len(states), bool(solution)))
        if not states: break
        newstates = []
        for state in states:
            if solution and state.cost >= solution.cost: continue    
            nodes = state.getNodes()
            for node in nodes:
                for edge in neighbours.get(node, []):
                    hasnewnodes = set(edge.getNodes()) - nodes 
                    if hasnewnodes:
                        newstate = state.appendToState(edge)
                        if solution and newstate.cost >= solution.cost: continue 
                        if newstate.isSolution(goal):
                            solution = newstate
                        else:
                            newstates.append(newstate)
        states = set(newstates)
    if solution:
        return [edge for edge in solution.edges if not isinstance(edge, StartEdge)]
