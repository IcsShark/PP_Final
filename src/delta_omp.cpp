#include <omp.h>

#include <algorithm>
#include <atomic>
#include <stdexcept>

#include "atomic_ops.hpp"
#include "sssp.hpp"

namespace {

// avoid false sharing between threads
struct alignas(64) PaddedU64 {
  uint64_t v = 0;
};

struct alignas(64) ThreadCounters {
  SsspStats s;
  uint64_t ph_edges = 0, ph_exp = 0, ph_max = 0;  // last phase (stats build)
};

// Per-thread barrier wait times, one entry per phase (stats build + phase log
// only). Each thread appends only to its own vector, so no synchronisation is
// needed; the vectors are merged after the parallel region.
struct alignas(64) ThreadWaits {
  std::vector<double> v;
};

}  // namespace

// OpenMP delta-stepping (proposal Algorithm 1 + Figure 2).
//
// The whole run is one parallel region, so threads are not forked and joined
// once per phase. Each iteration of the main loop:
//   1. select:  every thread reports the smallest non-empty bucket in its own
//               RingBins; after a barrier every thread computes the same
//               global minimum, so control flow stays identical everywhere
//               and no `single` is needed.
//   2. gather:  the per-thread slots of that bucket are concatenated into the
//               shared frontier (prefix sum over per-thread sizes). With
//               Filter::Merge, stale entries are dropped first.
//   3. relax:   `omp for schedule(runtime)` over the frontier. dist[] is
//               updated with atomic_min and improved vertices go into the
//               thread's own RingBins (no shared container, no contention).
// LightHeavy: phases relax light edges only; once bucket `cur` is empty, its
// expanded vertices (`settled`, deduplicated via settled_epoch) are gathered
// and their heavy edges are relaxed in one extra pass.
void delta_stepping_omp(const CSRGraph& g, vid_t src, const DeltaOptions& opt, int nthreads, DeltaWorkspace& ws,
                        std::vector<dist_t>& dist, SsspStats& stats, std::vector<PhaseRecord>* phase_log) {
  if (opt.delta == 0) throw std::invalid_argument("delta must be >= 1");
  if (nthreads < 1) throw std::invalid_argument("threads must be >= 1");
  const bool lh = opt.variant == Variant::LightHeavy;
  if (lh && !g.sorted_by_weight) throw std::invalid_argument("light/heavy variant needs weight-sorted adjacency");

  const dist_t delta = opt.delta;
  const weight_t w_max = opt.w_max ? opt.w_max : max_weight(g);
  const uint64_t R = ring_slots(w_max, opt);
  const uint64_t n = g.n;
  const bool merge_filter = opt.filter == Filter::Merge;

  stats = {};
  if (phase_log) phase_log->clear();
  dist.resize(n);
  ws.prepare(n, nthreads, lh);

  std::vector<PaddedU64> nexts(nthreads), sizes(nthreads), ssizes(nthreads);
  std::vector<ThreadCounters> tc(nthreads);
#ifdef SSSP_STATS
  std::vector<ThreadWaits> waits(phase_log ? nthreads : 0);
#endif

  const eid_t* off = g.offsets.data();
  const vid_t* dst = g.dst.data();
  const weight_t* wt = g.wt.data();
  dist_t* D = dist.data();
  uint32_t* SE = lh ? ws.settled_epoch.data() : nullptr;
  const uint64_t epoch_start = ws.epoch + 1;
  uint64_t epoch_end = epoch_start;

  auto light_end = [&](vid_t u) -> eid_t {
    return static_cast<eid_t>(
        std::upper_bound(wt + off[u], wt + off[u + 1], delta, [](dist_t d, weight_t w) { return d < w; }) - wt);
  };

#pragma omp parallel num_threads(nthreads)
  {
    const int tid = omp_get_thread_num();
    const int T = omp_get_num_threads();
    RingBins& my = ws.bins[tid];
    my.prepare(R);
    std::vector<vid_t>& mys = ws.settled[tid];
    mys.clear();
    ThreadCounters& c = tc[tid];

#pragma omp for schedule(static)
    for (uint64_t i = 0; i < n; ++i) D[i] = INF;
    if (tid == 0) {
      D[src] = 0;
      my.push(0, src);
    }

    // Thread-private copies of the control state. Every thread computes them
    // from the same shared inputs, so they stay identical across threads.
    uint64_t cur = 0, last_phase_bucket = NO_BUCKET, epoch = epoch_start;

    // Concatenate every thread's `local` into `shared`; returns total size.
    auto gather = [&](std::vector<vid_t>& local, std::vector<vid_t>& shared) -> uint64_t {
      // Read the capacity BEFORE the barrier: nobody can be resizing `shared`
      // here, so every thread sees the same value and takes the same branch
      // below. (Reading shared.size() after the barrier let a late thread see
      // the already-resized vector, skip the `single`, and desynchronise the
      // barriers -> intermittent deadlock.)
      const uint64_t cap = shared.size();
      sizes[tid].v = local.size();
#pragma omp barrier
      uint64_t offset = 0, total = 0;
      for (int t = 0; t < T; ++t) {
        if (t == tid) offset = total;
        total += sizes[t].v;
      }
      if (total > cap) {  // identical decision on every thread (same total, same cap)
#pragma omp single
        shared.resize(std::max<uint64_t>(total, 2 * cap));
      }
      std::copy(local.begin(), local.end(), shared.begin() + static_cast<std::ptrdiff_t>(offset));
      local.clear();
#pragma omp barrier
      return total;
    };

    // mode 0: all edges, 1: light edges only, 2: heavy edges of settled vertices.
    auto relax = [&](const vid_t* list, uint64_t cnt, int mode) {
      uint64_t pe = 0, px = 0, pm = 0;
#pragma omp for schedule(runtime) nowait
      for (uint64_t k = 0; k < cnt; ++k) {
        const vid_t u = list[k];
        const dist_t du = atomic_load_relaxed(D[u]);
        eid_t b = off[u], e = off[u + 1];
        if (mode == 2) {
          b = light_end(u);
        } else {
          if (du / delta != cur) {
            if constexpr (kStatsEnabled) ++c.s.stale;
            continue;
          }
          if (mode == 1) {
            e = light_end(u);
            const uint32_t ep = static_cast<uint32_t>(epoch);
            if (std::atomic_ref<uint32_t>(SE[u]).exchange(ep, std::memory_order_relaxed) != ep) mys.push_back(u);
          }
          if constexpr (kStatsEnabled) ++px;
        }
        if constexpr (kStatsEnabled) {
          pe += e - b;
          pm = std::max<uint64_t>(pm, e - b);
        }
        for (eid_t i = b; i < e; ++i) {
          const dist_t nd = du + wt[i];
          const vid_t v = dst[i];
          if (atomic_min(D[v], nd)) {
            if constexpr (kStatsEnabled) ++c.s.relax_ok;
            my.push(nd / delta, v);
          }
        }
      }
      if constexpr (kStatsEnabled) {
        c.s.expansions += px;
        c.s.edges_scanned += pe;
        c.ph_edges = pe;
        c.ph_exp = px;
        c.ph_max = pm;
      }
#ifdef SSSP_STATS
      // Barrier wait = idle time caused by imbalance. #ifdef (not if constexpr)
      // so the timing build does not even capture `waits`: its machine code
      // stays identical to the version without this measurement.
      const double wait_start = phase_log ? omp_get_wtime() : 0.0;
#endif
#pragma omp barrier
#ifdef SSSP_STATS
      // Stored in the thread's own vector; thread 0 must not read other
      // threads' values here (they may not have written them yet).
      if (phase_log) waits[tid].v.push_back(omp_get_wtime() - wait_start);
#endif
      if (tid == 0) {
        ++stats.phases;
        if (mode == 2) {
          ++stats.heavy_passes;
        } else if (cur != last_phase_bucket) {
          ++stats.buckets;
        }
        if constexpr (kStatsEnabled) {
          if (phase_log) {
            PhaseRecord r{cur, mode == 2, cnt, 0, 0, 0};
            for (int t = 0; t < T; ++t) {
              r.expanded += tc[t].ph_exp;
              r.edges += tc[t].ph_edges;
              r.max_vertex_edges = std::max(r.max_vertex_edges, tc[t].ph_max);
              r.max_thread_edges = std::max(r.max_thread_edges, tc[t].ph_edges);
            }
            if (mode == 2) r.expanded = cnt;
            phase_log->push_back(r);
          }
        }
      }
      if (mode != 2) last_phase_bucket = cur;
    };

    while (true) {
      // ---- 1. select
      nexts[tid].v = my.next(cur);
      if (lh) ssizes[tid].v = mys.size();
#pragma omp barrier
      uint64_t nb = NO_BUCKET, settled_total = 0;
      for (int t = 0; t < T; ++t) {
        nb = std::min(nb, nexts[t].v);
        settled_total += ssizes[t].v;
      }

      if (lh && settled_total > 0 && nb != cur) {
        // Bucket `cur` is finished: one pass over the heavy edges.
        const uint64_t h = gather(mys, ws.heavy);
        relax(ws.heavy.data(), h, 2);
        continue;
      }
      if (nb == NO_BUCKET) break;
      if (nb != cur) {
        cur = nb;
        ++epoch;
      }
      my.advance(cur);  // pulls overflow entries that now fit the window

      // ---- 2. gather (merge & filter)
      std::vector<vid_t>& slot = my.slot(cur);
      my.taken(cur);
      if (merge_filter) {
        const size_t before = slot.size();
        slot.erase(std::remove_if(slot.begin(), slot.end(), [&](vid_t v) { return D[v] / delta != cur; }),
                   slot.end());
        if constexpr (kStatsEnabled) c.s.merge_dropped += before - slot.size();
      }
      const uint64_t f = gather(slot, ws.frontier);
      if (f == 0) continue;  // bucket held only stale entries: no phase

      // ---- 3. relax
      relax(ws.frontier.data(), f, lh ? 1 : 0);
    }
    if (tid == 0) epoch_end = epoch;
  }

  ws.epoch = epoch_end;
  if constexpr (kStatsEnabled) {
#ifdef SSSP_STATS
    if (phase_log) {
      // Every thread executed every relax() and pushed exactly one wait per
      // phase, so each non-empty vector has one entry per PhaseRecord.
      const size_t P = phase_log->size();
      std::vector<const std::vector<double>*> per_thread;
      for (const ThreadWaits& w : waits)
        if (!w.v.empty() || P == 0) per_thread.push_back(&w.v);
      for (const auto* w : per_thread)
        if (w->size() != P) throw std::logic_error("barrier wait log does not match phase log");
      for (size_t i = 0; i < P && !per_thread.empty(); ++i) {
        double mx = 0, sum = 0;
        for (const auto* w : per_thread) {
          mx = std::max(mx, (*w)[i]);
          sum += (*w)[i];
        }
        (*phase_log)[i].max_wait_s = mx;
        (*phase_log)[i].mean_wait_s = sum / static_cast<double>(per_thread.size());
      }
    }
#endif
    for (const ThreadCounters& t : tc) {
      stats.edges_scanned += t.s.edges_scanned;
      stats.relax_ok += t.s.relax_ok;
      stats.expansions += t.s.expansions;
      stats.stale += t.s.stale;
      stats.merge_dropped += t.s.merge_dropped;
    }
  }
}
