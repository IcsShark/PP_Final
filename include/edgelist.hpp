#pragma once
#include <string>
#include <vector>

#include "graph.hpp"

struct EdgeListData {
  uint64_t n = 0;
  std::vector<Edge> edges;
  bool has_weights = false;
};

// 9th DIMACS challenge .gr: "p sp n m" header, "a u v w" arcs, 1-indexed.
EdgeListData read_dimacs(const std::string& path);

// SNAP / GAPBS style: "u v" or "u v w" per line; lines starting with # or %
// are comments. n = max id + 1 (after subtracting 1 if one_indexed).
EdgeListData read_edge_list(const std::string& path, bool one_indexed);

// Uniform random integer weights in [lo, hi_exclusive), deterministic in seed
// and input edge order.
void assign_random_weights(std::vector<Edge>& edges, weight_t lo, weight_t hi_exclusive, uint64_t seed);

// GAPBS .wel text format ("u v w" per directed edge, 0-indexed), so GAPBS
// can be run on exactly the same graph and weights.
void write_wel(const CSRGraph& g, const std::string& path);
