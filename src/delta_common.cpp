#include <algorithm>
#include <stdexcept>

#include "sssp.hpp"

void DeltaWorkspace::prepare(uint64_t n, int threads, bool need_epoch) {
  if (bins.size() < static_cast<size_t>(threads)) bins.resize(threads);
  if (settled.size() < static_cast<size_t>(threads)) settled.resize(threads);
  if (frontier.empty()) frontier.resize(std::max<uint64_t>(n, 1));
  // settled_epoch[v] == epoch means v was already put into `settled` during the
  // current bucket. Epochs keep increasing across runs; reset before overflow.
  if (need_epoch && (settled_epoch.size() != n || epoch > 0xF0000000ULL)) {
    settled_epoch.assign(n, 0);
    epoch = 0;
  }
}

uint64_t ring_slots(weight_t w_max, const DeltaOptions& opt) {
  if (opt.ring_cap == 0) throw std::invalid_argument("ring_cap must be >= 1");
  return std::min<uint64_t>(w_max / opt.delta + 2, opt.ring_cap);
}

weight_t max_weight(const CSRGraph& g) {
  weight_t w = 0;
#pragma omp parallel for reduction(max : w)
  for (uint64_t i = 0; i < g.m; ++i) w = std::max(w, g.wt[i]);
  return w;
}

const char* to_string(Variant v) { return v == Variant::AllEdges ? "all" : "lh"; }
const char* to_string(Filter f) { return f == Filter::Pop ? "pop" : "merge"; }
