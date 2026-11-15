// Graph Profiler: degree / weight statistics and the candidate delta values
// of proposal Section 3.5, printed as JSON.
#include <algorithm>
#include <cstdio>
#include <stdexcept>
#include <string>

#include "graph.hpp"

int main(int argc, char** argv) {
  if (argc != 2) {
    std::fprintf(stderr, "usage: %s GRAPH.csr\n", argv[0]);
    return 2;
  }
  try {
    const CSRGraph g = load_csr(argv[1]);
    const GraphProfile p = profile_graph(g);
    const double W = static_cast<double>(p.w_max);
    std::printf("{\n");
    std::printf("  \"graph\": \"%s\",\n", argv[1]);
    std::printf("  \"n\": %llu,\n  \"m\": %llu,\n", (unsigned long long)p.n, (unsigned long long)p.m);
    std::printf("  \"d_avg\": %.4f,\n  \"d_max\": %llu,\n", p.d_avg, (unsigned long long)p.d_max);
    std::printf("  \"w_min\": %u,\n  \"w_max\": %u,\n", p.w_min, p.w_max);
    std::printf("  \"zero_out_degree\": %llu,\n", (unsigned long long)p.zero_out_degree);
    std::printf("  \"sorted_by_weight\": %s,\n", g.sorted_by_weight ? "true" : "false");
    // Theta(W/d) rule for random weights, with d = d_max and d = d_avg.
    std::printf("  \"delta_rule_dmax\": %.2f,\n", p.d_max ? W / static_cast<double>(p.d_max) : 0.0);
    std::printf("  \"delta_rule_davg\": %.2f,\n", p.d_avg > 0 ? W / p.d_avg : 0.0);
    std::printf("  \"delta_sweep\": [");
    const uint64_t base = std::max<uint64_t>(p.w_min, 1);
    bool first = true;
    for (uint64_t d = base;; d *= 2) {
      std::printf("%s%llu", first ? "" : ", ", (unsigned long long)d);
      first = false;
      if (d >= p.w_max) break;
    }
    std::printf("]\n}\n");
    return 0;
  } catch (const std::exception& e) {
    std::fprintf(stderr, "error: %s\n", e.what());
    return 2;
  }
}
