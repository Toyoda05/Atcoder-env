from cp_lib.dsu import DSU
import sys


def solve():
    input = sys.stdin.buffer.readline
    n, q = map(int, input().split())
    uf = DSU(n)
    for _ in range(q):
        kind, a, b = map(int, input().split())
        if kind == 0:
            uf.merge(a, b)
        else:
            print(int(uf.same(a, b)))


if __name__ == "__main__":
    solve()
