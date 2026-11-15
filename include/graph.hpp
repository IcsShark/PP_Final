#pragma once
#include <string>
#include <vector>

#include "types.hpp"

struct Edge {
  vid_t u, v;
  weight_t w;
};

// Compressed sparse row graph (directed). Out-edges of u are
// dst[offsets[u] .. offsets[u+1]) with weights wt[...] at the same indices.
struct CSRGraph {
  uint64_t n = 0;
  uint64_t m = 0;
  bool sorted_by_weight = false;  // each adjacency list sorted by (weight, dst)
  std::vector<eid_t> offsets;     // n + 1
  std::vector<vid_t> dst;         // m
  std::vector<weight_t> wt;       // m

  uint64_t degree(vid_t u) const { return offsets[u + 1] - offsets[u]; }
};

struct BuildOptions {
  bool symmetrize = false;         // add reverse edge (same weight) for every input edge
  bool remove_self_loops = true;
  bool dedup = true;               // collapse parallel edges, keeping the minimum weight
  bool sort_by_weight = true;      // needed by the light/heavy variant
};

CSRGraph build_csr(uint64_t n, const std::vector<Edge>& edges, const BuildOptions& opt);

// Re-sorts every adjacency list by (weight, dst). Used when a .csr file was
// written without sorting but the light/heavy variant is requested.
void sort_adjacency_by_weight(CSRGraph& g);

// Binary format: header {magic "SSSPCSR1", n, m, flags, reserved},
// then offsets[n+1] (u64), dst[m] (u32), wt[m] (u32). Little endian.
void save_csr(const CSRGraph& g, const std::string& path);
CSRGraph load_csr(const std::string& path);

struct GraphProfile {
  uint64_t n = 0, m = 0;
  double d_avg = 0;
  uint64_t d_max = 0;
  weight_t w_min = 0, w_max = 0;
  uint64_t zero_out_degree = 0;
};

GraphProfile profile_graph(const CSRGraph& g);
