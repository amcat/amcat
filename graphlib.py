import heapq

def shortest_path(G, start, end):
    def flatten(L):       # Flatten linked list of form [0,[1,[2,[]]]]
        while len(L) > 0:
            yield L[0]
            L = L[1]

    q = [(0, start, ())]  # Heap of (cost, path_head, path_rest).
    visited = set()       # Visited vertices.
    while True:
        (cost, v1, path) = heapq.heappop(q)
        if v1 not in visited:
            visited.add(v1)
            if v1 == end:
                return list(flatten(path))[::-1] + [v1]
            path = (v1, path)
            for (v2, cost2) in G[v1].iteritems():
                if v2 not in visited:
                    heapq.heappush(q, (cost + cost2, v2, path))

if __name__ == '__main__':
    G = {'a' : {'b':1, 'c':1},
         'b' : {'d':1},
         'c' : {'e' : 1},
         'd' : {'f':1, 'e':1},
         'e' : {'f':1},
         }

    print shortest_path(G, 'a', 'f')
         
