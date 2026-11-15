#include "generators.hpp"

#include <omp.h>

#include <algorithm>
#include <numeric>
#include <random>
#include <stdexcept>

namespace {

constexpr uint64_t kBlock = 1 << 16;

// Independent, deterministic RNG stream per block of edges, so generation
// can run in parallel and still be reproducible for a given seed.
std::mt19937_64 block_rng(uint64_t seed, uint64_t block) {
  return std::mt19937_64(seed ^ (0x9E3779B97F4A7C15ULL * (block + 1)));
}

void check_scale(int scale, int degree) {
  if (scale < 1 || scale > 31) throw std::invalid_argument("scale must be in [1, 31]");
  if (degree < 1) throw std::invalid_argument("degree must be >= 1");
}

}  // namespace

std::vector<Edge> gen_kronecker(int scale, int degree, uint64_t seed) {
  check_scale(scale, degree);
  const uint64_t n = uint64_t{1} << scale;
  const uint64_t m = n * static_cast<uint64_t>(degree) / 2;
  const double A = 0.57, B = 0.19, C = 0.19;
  std::vector<Edge> edges(m);
  const int64_t nblocks = static_cast<int64_t>((m + kBlock - 1) / kBlock);

#pragma omp parallel for schedule(static)
  for (int64_t bk = 0; bk < nblocks; ++bk) {
    auto rng = block_rng(seed, static_cast<uint64_t>(bk));
    std::uniform_real_distribution<double> U(0.0, 1.0);
    const uint64_t b = static_cast<uint64_t>(bk) * kBlock, e = std::min(m, b + kBlock);
    for (uint64_t i = b; i < e; ++i) {
      uint64_t u = 0, v = 0;
      for (int d = 0; d < scale; ++d) {
        const double r = U(rng);
        u <<= 1;
        v <<= 1;
        if (r < A) {
        } else if (r < A + B) {
          v |= 1;
        } else if (r < A + B + C) {
          u |= 1;
        } else {
          u |= 1;
          v |= 1;
        }
      }
      edges[i] = {static_cast<vid_t>(u), static_cast<vid_t>(v), 0};
    }
  }

  std::vector<vid_t> perm(n);
  std::iota(perm.begin(), perm.end(), vid_t{0});
  std::mt19937_64 prng(seed + 1);
  std::shuffle(perm.begin(), perm.end(), prng);
#pragma omp parallel for schedule(static)
  for (int64_t i = 0; i < static_cast<int64_t>(m); ++i) {
    edges[i].u = perm[edges[i].u];
    edges[i].v = perm[edges[i].v];
  }
  return edges;
}

std::vector<Edge> gen_uniform(int scale, int degree, uint64_t seed) {
  check_scale(scale, degree);
  const uint64_t n = uint64_t{1} << scale;
  const uint64_t m = n * static_cast<uint64_t>(degree) / 2;
  std::vector<Edge> edges(m);
  const int64_t nblocks = static_cast<int64_t>((m + kBlock - 1) / kBlock);

#pragma omp parallel for schedule(static)
  for (int64_t bk = 0; bk < nblocks; ++bk) {
    auto rng = block_rng(seed, static_cast<uint64_t>(bk));
    std::uniform_int_distribution<uint64_t> V(0, n - 1);
    const uint64_t b = static_cast<uint64_t>(bk) * kBlock, e = std::min(m, b + kBlock);
    for (uint64_t i = b; i < e; ++i) {
      const uint64_t u = V(rng);
      const uint64_t v = V(rng);
      edges[i] = {static_cast<vid_t>(u), static_cast<vid_t>(v), 0};
    }
  }
  return edges;
}

std::vector<Edge> gen_grid2d(uint64_t side) {
  if (side < 2 || side * side >= (uint64_t{1} << 32)) throw std::invalid_argument("grid side out of range");
  std::vector<Edge> edges;
  edges.reserve(2 * side * (side - 1));
  for (uint64_t r = 0; r < side; ++r) {
    for (uint64_t c = 0; c < side; ++c) {
      const vid_t id = static_cast<vid_t>(r * side + c);
      if (c + 1 < side) edges.push_back({id, static_cast<vid_t>(id + 1), 0});
      if (r + 1 < side) edges.push_back({id, static_cast<vid_t>(id + side), 0});
    }
  }
  return edges;
}
