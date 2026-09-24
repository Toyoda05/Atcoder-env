#include <iostream>
#include "cp/dsu.hpp"
#include <atcoder/dsu>

int main() {
    int n, q;
    std::cin >> n >> q;
    cp::DSU uf(n);
    atcoder::dsu reference(n);
    while (q--) {
        int kind, a, b;
        std::cin >> kind >> a >> b;
        if (kind == 0) {
            uf.merge(a, b);
            reference.merge(a, b);
        } else {
            if (uf.same(a, b) != reference.same(a, b)) return 1;
            std::cout << uf.same(a, b) << '\n';
        }
    }
}
