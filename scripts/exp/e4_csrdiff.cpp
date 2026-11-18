// E4 diagnostic (built by e4_check_ref.sh, not part of the library): compare
// two CSR files A and B vertex by vertex, and check that each is a valid
// output of build_csr (adjacency sorted by (weight, dst), no duplicate dst,
// no self loop).
//
//   e4_csrdiff A.csr B.csr
#include <algorithm>
#include <cstdio>
#include <utility>
#include <vector>

#include "graph.hpp"

int main(int argc, char** argv) {
  if (argc != 3) {
    std::fprintf(stderr, "usage: %s A.csr B.csr\n", argv[0]);
    return 2;
  }
  CSRGraph a = load_csr(argv[1]), b = load_csr(argv[2]);
  std::printf("A n=%llu m=%llu | B n=%llu m=%llu\n", (unsigned long long)a.n, (unsigned long long)a.m,
              (unsigned long long)b.n, (unsigned long long)b.m);

  for (const CSRGraph* g : {&a, &b}) {
    uint64_t bad_order = 0, dup = 0, loops = 0;
    std::vector<vid_t> nb;
    for (uint64_t u = 0; u < g->n; ++u) {
      nb.clear();
      for (eid_t i = g->offsets[u]; i < g->offsets[u + 1]; ++i) {
        if (i > g->offsets[u] &&
            std::make_pair(g->wt[i - 1], g->dst[i - 1]) > std::make_pair(g->wt[i], g->dst[i]))
          ++bad_order;
        if (g->dst[i] == u) ++loops;
        nb.push_back(g->dst[i]);
      }
      std::sort(nb.begin(), nb.end());
      for (size_t k = 1; k < nb.size(); ++k) dup += nb[k] == nb[k - 1];
    }
    std::printf("%s: out-of-order=%llu duplicate-dst=%llu self-loops=%llu\n", g == &a ? "A" : "B",
                (unsigned long long)bad_order, (unsigned long long)dup, (unsigned long long)loops);
  }

  if (a.n != b.n || a.m != b.m || a.offsets != b.offsets) {
    std::printf("offsets differ: not comparing adjacency\n");
    return 1;
  }
  uint64_t vdiff = 0, wdiff = 0, ndiff = 0, shown = 0;
  std::vector<std::pair<vid_t, weight_t>> x, y;
  for (uint64_t u = 0; u < a.n; ++u) {
    const eid_t s = a.offsets[u], e = a.offsets[u + 1];
    bool same = true;
    for (eid_t i = s; i < e && same; ++i) same = a.dst[i] == b.dst[i] && a.wt[i] == b.wt[i];
    if (same) continue;
    ++vdiff;
    x.clear();
    y.clear();
    for (eid_t i = s; i < e; ++i) {
      x.push_back({a.dst[i], a.wt[i]});
      y.push_back({b.dst[i], b.wt[i]});
    }
    std::sort(x.begin(), x.end());
    std::sort(y.begin(), y.end());
    for (size_t k = 0; k < x.size(); ++k) {
      if (x[k].first != y[k].first) ++ndiff;
      else if (x[k].second != y[k].second) ++wdiff;
    }
    if (shown++ < 3) {
      std::printf("vertex %llu (degree %llu), first neighbours as (dst,w) sorted by dst:\n  A:",
                  (unsigned long long)u, (unsigned long long)(e - s));
      for (size_t k = 0; k < std::min<size_t>(x.size(), 6); ++k) std::printf(" (%u,%u)", x[k].first, x[k].second);
      std::printf("\n  B:");
      for (size_t k = 0; k < std::min<size_t>(y.size(), 6); ++k) std::printf(" (%u,%u)", y[k].first, y[k].second);
      std::printf("\n");
    }
  }
  std::printf("vertices with different adjacency: %llu of %llu\n", (unsigned long long)vdiff,
              (unsigned long long)a.n);
  std::printf("same dst, different weight: %llu; different dst: %llu\n", (unsigned long long)wdiff,
              (unsigned long long)ndiff);
  return vdiff ? 1 : 0;
}
