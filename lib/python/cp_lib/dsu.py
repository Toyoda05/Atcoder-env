class DSU:
    """Disjoint-set union: amortized O(alpha(n)) merge/same, O(n) memory."""

    def __init__(self, n):
        self._parent_or_size = [-1] * n

    def leader(self, a):
        p = self._parent_or_size
        root = a
        while p[root] >= 0:
            root = p[root]
        while a != root:
            parent = p[a]
            p[a] = root
            a = parent
        return root

    def merge(self, a, b):
        a, b = self.leader(a), self.leader(b)
        if a == b:
            return a
        p = self._parent_or_size
        if p[a] > p[b]:
            a, b = b, a
        p[a] += p[b]
        p[b] = a
        return a

    def same(self, a, b):
        return self.leader(a) == self.leader(b)

    def size(self, a):
        return -self._parent_or_size[self.leader(a)]
