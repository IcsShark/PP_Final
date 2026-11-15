#pragma once
#include <vector>

#include "graph.hpp"

// All generators return *undirected* edge lists (one entry per edge, weight 0);
// build them with BuildOptions::symmetrize = true and assign weights first.
// With symmetrize, the average out-degree is about `degree`.

// Kronecker / R-MAT with GAPBS / Graph500 parameters A=0.57, B=C=0.19.
// Vertex ids are randomly permuted to remove id locality.
std::vector<Edge> gen_kronecker(int scale, int degree, uint64_t seed);

// Uniform random (Erdos-Renyi style) endpoints.
std::vector<Edge> gen_uniform(int scale, int degree, uint64_t seed);

// side x side 2D grid, 4-neighbour connectivity. Vertex id = row * side + col.
std::vector<Edge> gen_grid2d(uint64_t side);
