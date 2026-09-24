#pragma once
#include <algorithm>
#include <cassert>
#include <vector>

namespace cp {
class DSU {
    std::vector<int> parent_or_size;
public:
    explicit DSU(int n) : parent_or_size(n, -1) {}
    int leader(int a) {
        assert(0 <= a && a < static_cast<int>(parent_or_size.size()));
        return parent_or_size[a] < 0 ? a : parent_or_size[a] = leader(parent_or_size[a]);
    }
    int merge(int a, int b) {
        a = leader(a); b = leader(b);
        if (a == b) return a;
        if (parent_or_size[a] > parent_or_size[b]) std::swap(a, b);
        parent_or_size[a] += parent_or_size[b];
        parent_or_size[b] = a;
        return a;
    }
    bool same(int a, int b) { return leader(a) == leader(b); }
    int size(int a) { return -parent_or_size[leader(a)]; }
};
}
