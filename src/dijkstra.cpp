#include <functional>
#include <queue>
#include <utility>

#include "sssp.hpp"

// Sequential binary-heap Dijkstra with lazy deletion. Serves as both the
// sequential baseline and the correctness oracle.
void dijkstra(const CSRGraph& g, vid_t src, std::vector<dist_t>& dist, SsspStats& stats) {
  stats = {};
  dist.assign(g.n, INF);
  using Item = std::pair<dist_t, vid_t>;
  std::priority_queue<Item, std::vector<Item>, std::greater<Item>> pq;
  dist[src] = 0;
  pq.push({0, src});
  while (!pq.empty()) {
    const auto [du, u] = pq.top();
    pq.pop();
    if (du != dist[u]) {
      if constexpr (kStatsEnabled) ++stats.stale;
      continue;
    }
    if constexpr (kStatsEnabled) {
      ++stats.expansions;
      stats.edges_scanned += g.offsets[u + 1] - g.offsets[u];
    }
    for (eid_t i = g.offsets[u]; i < g.offsets[u + 1]; ++i) {
      const vid_t v = g.dst[i];
      const dist_t nd = du + g.wt[i];
      if (nd < dist[v]) {
        dist[v] = nd;
        if constexpr (kStatsEnabled) ++stats.relax_ok;
        pq.push({nd, v});
      }
    }
  }
}
