
import toolkit
from idlabel import Identity

def profile(s):
    pass
    #toolkit.ticker.warn(s)

#trans = lambda a:str(a)##

#def p(x):
#    if type(x) == tuple:
#        return "->".join(map(p, x))
#    if type(x) in (set, list):
#        return "(%s)" % ",".join(map(p,x))
#    return trans(x)
    

class MSTProblem(object):
    def __init__(self):
        self.goals = []
        self.edges = {} # {nodea : {nodeb : cost}}
    def addgoal(self, a):
        self.goals.append(a)
    def addedge(self, a, b, cost):
        if a not in self.edges: self.edges[a] = {}
        if b not in self.edges: self.edges[b] = {}
        self.edges[a][b] = cost
        self.edges[b][a] = cost

    def normalize(self):
        edges, goal, extra = self.edges, set(self.goals), []
        #print "normalize:", edges, goal, extra
        if self.prune:
            changed = True
            while changed:
                changed = False
                for considergoal in (False, True):
                    for a, bs in edges.items():
                        if len(bs) == 1:
                            if a in goal and not considergoal: continue
                            #print "Deleting node %s" % p(a)
                            # We can safely delete a node only connected to one other node
                            if a in goal:
                                # But if that nodes  was on the goal, we replace it in the goal
                                # by the other node, and add an node->other edge to the solution

                                b = bs.keys()[0]
                                extra.append((a,b))
                                goal.remove(a)
                                goal.add(b)
                                #print "%s was on goal, adding %s->%s to extra and %s to goal, extra=%s, goal=%s" % (p(a),p(a),p(b),p(b), p(extra), p(goal))
                            del edges[a]
                            for b in edges:
                                if a in edges[b]:
                                    del edges[b][a]
                            changed = True
                            break
                    if changed: break
        return edges, goal, extra
        
    def solve(self):
        edges, goal, extra = self.normalize()
        #print "solve:", edges, goal, extra
        for node in goal:
            if node not in edges: raise Exception("Goal node %s not found in edges (goal=%r)" % (node, goal))
        states = []
        solution = None # best state so far
        #TODO addition + cost check logic appears twice, abstract?
        for g in goal:
            state = State(((None, g),), 0)
            if solution and state.cost >= solution.cost: continue
            if isSolution(goal, state):
                solution = state
            states.append(state)
            break
        profile(solution)
        while True:
            profile("Next Iteration, #states %i, solutions? %s" % (len(states), solution and solution.cost))
            if not states: break
            newstates = set()
            for state in states:
                profile("State cost: %s, solution.cost:%s" % (state.cost, solution and solution.cost))
                if solution and state.cost >= solution.cost: continue
                for a in state.nodes:
                    for b, cost in edges[a].iteritems():
                        if b in state.nodes: continue # b already in state
                        newstate = state.nextState(a,b,cost)
                        if solution and newstate.cost >= solution.cost: continue
                        profile("Newstate cost: %s, solution.cost:%s" % (newstate.cost, solution and solution.cost))
                        if isSolution(goal, newstate):
                            solution = newstate
                            profile("Solution!")
                        else:
                            newstates.add(newstate)
            states = newstates
        if solution:
            return solution.edges + tuple(extra)

def isSolution(goals, state):
    for g in goals:
        if g not in state.nodes: return False
    return True
        
def getSolution(mappings, goal, prune=True):
    """
    Calculate nodes to numbers and add edges to MSTProblem
    Re-converts solution from edge=number tuple to mappings 
    """
    #print ">>>", goal
    edges = {}
    nodes = toolkit.Indexer()
    p = MSTProblem()
    p.prune = prune
    for g in goal:
        p.addgoal(nodes.getNumber(g))
    for m in mappings:
        a, b = nodes.getNumbers(m.a, m.b)
        p.addedge(a,b, m.getCost())
        edges[a,b] = m
        edges[b,a] = m
    sol = []
    #def tr(x):
    #    if type(x) == int:
    #        return "%i:%s" % (x, nodes.objects[x])
    #    raise Exception(x)
    #global trans
    #trans = tr
    for edge in p.solve():
        if edge[0] is None: continue
        sol.append(edges[edge])
    return sol
    
        
class State(Identity):
    def __init__(self, edges=(), cost=0, nodes = None):
        self.edges = edges
        self.cost = cost
        if nodes is None:
            nodes = set()
            for a,b in self.edges:
                [nodes.add(x) for x in (a,b) if x is not None]
        self.nodes = nodes
    def identity(self):
        return self.edges, self.cost
    def isSolution(self, goal):
        return not (goal - nodes)
    def nextState(self, a, b, cost):
        nodes = set(self.nodes)
        [nodes.add(x) for x in (a,b) if x is not None]
        if a > b: b,a = a,b
        newedges = tuple(sorted(self.edges + ((a,b),)))
        newcost = self.cost + cost
        return State(newedges, newcost, nodes)

