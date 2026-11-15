#include "graph.hpp"

#include <omp.h>

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <utility>

namespace {

constexpr char kMagic[8] = {'S', 'S', 'S', 'P', 'C', 'S', 'R', '1'};
constexpr uint64_t kFlagSorted = 1;

struct CSRHeader {
  char magic[8];
  uint64_t n, m, flags, reserved;
};

// Per-vertex normalisation: optional dedup (keep min weight per dst) and
// optional sort by (weight, dst). Compacts the arrays if dedup removed edges.
void normalize_adjacency(CSRGraph& g, bool dedup, bool sort_w) {
  const uint64_t n = g.n;
  std::vector<eid_t> new_deg(n + 1, 0);

#pragma omp parallel
  {
    std::vector<std::pair<uint64_t, uint64_t>> tmp;  // (key1, key2) packed per edge
#pragma omp for schedule(dynamic, 1024)
    for (uint64_t u = 0; u < n; ++u) {
      const eid_t b = g.offsets[u], e = g.offsets[u + 1];
      uint64_t k = e - b;
      if (dedup && k > 1) {
        tmp.clear();
        for (eid_t i = b; i < e; ++i) tmp.emplace_back(g.dst[i], g.wt[i]);
        std::sort(tmp.begin(), tmp.end());  // by dst, then weight -> first of each dst is the min
        uint64_t out = 0;
        for (uint64_t i = 0; i < tmp.size(); ++i) {
          if (i > 0 && tmp[i].first == tmp[i - 1].first) continue;
          g.dst[b + out] = static_cast<vid_t>(tmp[i].first);
          g.wt[b + out] = static_cast<weight_t>(tmp[i].second);
          ++out;
        }
        k = out;
      }
      if (sort_w && k > 1) {
        tmp.clear();
        for (eid_t i = b; i < b + k; ++i) tmp.emplace_back(g.wt[i], g.dst[i]);
        std::sort(tmp.begin(), tmp.end());
        for (uint64_t i = 0; i < k; ++i) {
          g.wt[b + i] = static_cast<weight_t>(tmp[i].first);
          g.dst[b + i] = static_cast<vid_t>(tmp[i].second);
        }
      }
      new_deg[u] = k;
    }
  }

  if (sort_w) g.sorted_by_weight = true;
  if (!dedup) return;

  std::vector<eid_t> new_off(n + 1, 0);
  for (uint64_t u = 0; u < n; ++u) new_off[u + 1] = new_off[u] + new_deg[u];
  const uint64_t new_m = new_off[n];
  if (new_m == g.m) return;

  std::vector<vid_t> nd(new_m);
  std::vector<weight_t> nw(new_m);
#pragma omp parallel for schedule(dynamic, 1024)
  for (uint64_t u = 0; u < n; ++u) {
    std::copy_n(g.dst.begin() + g.offsets[u], new_deg[u], nd.begin() + new_off[u]);
    std::copy_n(g.wt.begin() + g.offsets[u], new_deg[u], nw.begin() + new_off[u]);
  }
  g.offsets.swap(new_off);
  g.dst.swap(nd);
  g.wt.swap(nw);
  g.m = new_m;
}

void read_exact(std::FILE* f, void* p, size_t bytes, const std::string& path) {
  if (bytes && std::fread(p, 1, bytes, f) != bytes) throw std::runtime_error("truncated file: " + path);
}

void write_exact(std::FILE* f, const void* p, size_t bytes, const std::string& path) {
  if (bytes && std::fwrite(p, 1, bytes, f) != bytes) throw std::runtime_error("write failed: " + path);
}

}  // namespace

CSRGraph build_csr(uint64_t n, const std::vector<Edge>& edges, const BuildOptions& opt) {
  if (n >= (uint64_t{1} << 32)) throw std::runtime_error("too many vertices for 32-bit ids");
  CSRGraph g;
  g.n = n;

  auto keep = [&](const Edge& e) { return !(opt.remove_self_loops && e.u == e.v); };

  std::vector<eid_t> pos(n + 1, 0);
  for (const Edge& e : edges) {
    if (e.u >= n || e.v >= n) throw std::runtime_error("edge endpoint out of range");
    if (!keep(e)) continue;
    ++pos[e.u + 1];
    if (opt.symmetrize) ++pos[e.v + 1];
  }
  for (uint64_t i = 0; i < n; ++i) pos[i + 1] += pos[i];
  g.offsets = pos;
  g.m = g.offsets[n];
  g.dst.resize(g.m);
  g.wt.resize(g.m);

  for (const Edge& e : edges) {
    if (!keep(e)) continue;
    eid_t p = pos[e.u]++;
    g.dst[p] = e.v;
    g.wt[p] = e.w;
    if (opt.symmetrize) {
      p = pos[e.v]++;
      g.dst[p] = e.u;
      g.wt[p] = e.w;
    }
  }

  if (opt.dedup || opt.sort_by_weight) normalize_adjacency(g, opt.dedup, opt.sort_by_weight);
  return g;
}

void sort_adjacency_by_weight(CSRGraph& g) {
  if (!g.sorted_by_weight) normalize_adjacency(g, false, true);
}

void save_csr(const CSRGraph& g, const std::string& path) {
  std::FILE* f = std::fopen(path.c_str(), "wb");
  if (!f) throw std::runtime_error("cannot open for writing: " + path);
  CSRHeader h{};
  std::memcpy(h.magic, kMagic, sizeof(kMagic));
  h.n = g.n;
  h.m = g.m;
  h.flags = g.sorted_by_weight ? kFlagSorted : 0;
  write_exact(f, &h, sizeof(h), path);
  write_exact(f, g.offsets.data(), g.offsets.size() * sizeof(eid_t), path);
  write_exact(f, g.dst.data(), g.dst.size() * sizeof(vid_t), path);
  write_exact(f, g.wt.data(), g.wt.size() * sizeof(weight_t), path);
  if (std::fclose(f) != 0) throw std::runtime_error("close failed: " + path);
}

CSRGraph load_csr(const std::string& path) {
  std::FILE* f = std::fopen(path.c_str(), "rb");
  if (!f) throw std::runtime_error("cannot open: " + path);
  CSRHeader h{};
  try {
    read_exact(f, &h, sizeof(h), path);
    if (std::memcmp(h.magic, kMagic, sizeof(kMagic)) != 0) throw std::runtime_error("not a SSSPCSR1 file: " + path);
    CSRGraph g;
    g.n = h.n;
    g.m = h.m;
    g.sorted_by_weight = (h.flags & kFlagSorted) != 0;
    g.offsets.resize(g.n + 1);
    g.dst.resize(g.m);
    g.wt.resize(g.m);
    read_exact(f, g.offsets.data(), g.offsets.size() * sizeof(eid_t), path);
    read_exact(f, g.dst.data(), g.dst.size() * sizeof(vid_t), path);
    read_exact(f, g.wt.data(), g.wt.size() * sizeof(weight_t), path);
    std::fclose(f);
    if (g.offsets[0] != 0 || g.offsets[g.n] != g.m) throw std::runtime_error("corrupt offsets in " + path);
    return g;
  } catch (...) {
    std::fclose(f);
    throw;
  }
}

GraphProfile profile_graph(const CSRGraph& g) {
  GraphProfile p;
  p.n = g.n;
  p.m = g.m;
  p.d_avg = g.n ? static_cast<double>(g.m) / static_cast<double>(g.n) : 0.0;
  uint64_t dmax = 0, zero = 0;
#pragma omp parallel for reduction(max : dmax) reduction(+ : zero)
  for (uint64_t u = 0; u < g.n; ++u) {
    const uint64_t d = g.offsets[u + 1] - g.offsets[u];
    dmax = std::max(dmax, d);
    zero += (d == 0);
  }
  weight_t wmin = g.m ? std::numeric_limits<weight_t>::max() : 0, wmax = 0;
#pragma omp parallel for reduction(min : wmin) reduction(max : wmax)
  for (uint64_t i = 0; i < g.m; ++i) {
    wmin = std::min(wmin, g.wt[i]);
    wmax = std::max(wmax, g.wt[i]);
  }
  p.d_max = dmax;
  p.zero_out_degree = zero;
  p.w_min = wmin;
  p.w_max = wmax;
  return p;
}
