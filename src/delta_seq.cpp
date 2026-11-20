#include <algorithm>
#include <stdexcept>

#include "sssp.hpp"

// Sequential delta-stepping. Same bucket structure, phase definition and
// variants as the OpenMP version, without atomics or barriers, so its
// phase/bucket counts match the parallel version run with one thread.
void delta_stepping_seq(const CSRGraph& g, vid_t src, const DeltaOptions& opt, DeltaWorkspace& ws,
                        std::vector<dist_t>& dist, SsspStats& stats, std::vector<PhaseRecord>* phase_log) {
  if (opt.delta == 0) throw std::invalid_argument("delta must be >= 1");
  const bool lh = opt.variant == Variant::LightHeavy;
  if (lh && !g.sorted_by_weight) throw std::invalid_argument("light/heavy variant needs weight-sorted adjacency");

  const dist_t delta = opt.delta;
  const weight_t w_max = opt.w_max ? opt.w_max : max_weight(g);
  const uint64_t R = ring_slots(w_max, opt);
  const eid_t* off = g.offsets.data();
  const vid_t* dst = g.dst.data();
  const weight_t* wt = g.wt.data();

  stats = {};
  if (phase_log) phase_log->clear();
  dist.resize(g.n);
  std::fill(dist.begin(), dist.end(), INF);
  ws.prepare(g.n, 1, lh);
  RingBins& bins = ws.bins[0];
  bins.prepare(R);
  std::vector<vid_t>& S = ws.settled[0];
  S.clear();
  std::vector<vid_t> F;  // frontier (swapped with ring slots, so no copy)

  auto light_end = [&](vid_t u) -> eid_t {
    return static_cast<eid_t>(
        std::upper_bound(wt + off[u], wt + off[u + 1], delta, [](dist_t d, weight_t w) { return d < w; }) - wt);
  };
  auto relax_edges = [&](dist_t du, eid_t b, eid_t e) {
    for (eid_t i = b; i < e; ++i) {
      const vid_t v = dst[i];
      const dist_t nd = du + wt[i];
      if (nd < dist[v]) {
        dist[v] = nd;
        if constexpr (kStatsEnabled) ++stats.relax_ok;
        bins.push(nd / delta, v);
      }
    }
  };

  dist[src] = 0;
  bins.push(0, src);
  uint64_t cur = 0, last_phase_bucket = NO_BUCKET;
  uint64_t epoch = ws.epoch + 1;

  while (true) {
    const uint64_t nb = bins.next(cur);

    if (lh && !S.empty() && nb != cur) {
      // Bucket `cur` is settled: relax the heavy edges of its vertices once.
      uint64_t pe = 0, pm = 0;
      for (vid_t u : S) {
        const eid_t b = light_end(u), e = off[u + 1];
        if constexpr (kStatsEnabled) {
          pe += e - b;
          pm = std::max<uint64_t>(pm, e - b);
        }
        relax_edges(dist[u], b, e);
      }
      ++stats.phases;
      ++stats.heavy_passes;
      if constexpr (kStatsEnabled) {
        stats.edges_scanned += pe;
        if (phase_log) phase_log->push_back({cur, true, S.size(), S.size(), pe, pm, pe});
      }
      S.clear();
      continue;
    }
    if (nb == NO_BUCKET) break;
    if (nb != cur) {
      cur = nb;
      ++epoch;
    }
    bins.advance(cur);  // pulls overflow entries that now fit the window

    // build frontier F (the vertices which will be expanded and used to relax their neighbors in this round)
    std::vector<vid_t>& slot = bins.slot(cur);
    bins.taken(cur);
    F.clear();
    F.swap(slot);
    if (opt.filter == Filter::Merge) {
      const size_t before = F.size();
      F.erase(std::remove_if(F.begin(), F.end(), [&](vid_t v) { return dist[v] / delta != cur; }), F.end());
      if constexpr (kStatsEnabled) stats.merge_dropped += before - F.size();
      if (F.empty()) continue;
    }

    ++stats.phases;
    if (cur != last_phase_bucket) {
      ++stats.buckets;
      last_phase_bucket = cur;
    }

    // Light phase
    uint64_t pe = 0, px = 0, pm = 0;
    for (vid_t u : F) {
      const dist_t du = dist[u];
      if (du / delta != cur) {
        if constexpr (kStatsEnabled) ++stats.stale;
        continue;
      }
      eid_t b = off[u], e = off[u + 1];
      if (lh) {
        e = light_end(u);
        if (ws.settled_epoch[u] != epoch) {  // make sure S does not contain duplicate vertices
          ws.settled_epoch[u] = static_cast<uint32_t>(epoch);
          S.push_back(u);
        }
      }
      if constexpr (kStatsEnabled) {
        ++px;
        pe += e - b;
        pm = std::max<uint64_t>(pm, e - b);
      }
      relax_edges(du, b, e);
    }
    if constexpr (kStatsEnabled) {
      stats.expansions += px;
      stats.edges_scanned += pe;
      if (phase_log) phase_log->push_back({cur, false, F.size(), px, pe, pm, pe});
    }
  }
  ws.epoch = epoch;
}
