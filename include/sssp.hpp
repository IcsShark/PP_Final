#pragma once
#include <string>
#include <vector>

#include "graph.hpp"
#include "ring_bins.hpp"

enum class Variant {
  AllEdges,    // Algorithm 1 in the proposal: relax every edge in every phase
  LightHeavy,  // Meyer & Sanders: light edges per phase, heavy edges once per bucket
};
enum class Filter {
  Pop,    // stale entries are skipped when popped (they still cost a phase)
  Merge,  // stale entries are dropped while forming the frontier
};

struct DeltaOptions {
  dist_t delta = 1;
  Variant variant = Variant::AllEdges;
  Filter filter = Filter::Pop;
  weight_t w_max = 0;  // max edge weight of the graph; 0 = compute it (O(m))
  // Upper bound on ring slots per thread (see ring_bins.hpp). Buckets beyond
  // the window go to an overflow list, so memory stays bounded for any delta.
  uint64_t ring_cap = uint64_t{1} << 19;
};

// Work / depth counters. phases, buckets and heavy_passes are always counted;
// the rest are counted only in the stats build (-DSSSP_STATS).
struct SsspStats {
  uint64_t phases = 0;         // synchronized relaxation rounds (incl. heavy passes)
  uint64_t buckets = 0;        // distinct buckets that ran at least one phase
  uint64_t heavy_passes = 0;   // light/heavy variant only
  uint64_t edges_scanned = 0;  // relaxation attempts
  uint64_t relax_ok = 0;       // successful atomic-min updates
  uint64_t expansions = 0;     // non-stale vertices popped and expanded
  uint64_t stale = 0;          // stale entries skipped at pop time
  uint64_t merge_dropped = 0;  // stale entries dropped at merge time (Filter::Merge)
};

// One row per phase (stats build only).
struct PhaseRecord {
  uint64_t bucket;
  bool heavy;
  uint64_t frontier;          // entries in the frontier (incl. stale)
  uint64_t expanded;          // vertices actually relaxed
  uint64_t edges;             // edges scanned in this phase
  uint64_t max_vertex_edges;  // largest single-vertex work item (load-imbalance bound)
};

// Scratch memory reused across runs so that allocation is not timed again
// for every repetition.
struct DeltaWorkspace {
  std::vector<RingBins> bins;                // one per thread
  std::vector<std::vector<vid_t>> settled;   // per-thread vertices expanded in the current bucket (light/heavy)
  std::vector<vid_t> frontier, heavy;        // shared arrays filled by gather
  std::vector<uint32_t> settled_epoch;       // dedupe for `settled`, light/heavy only
  uint64_t epoch = 0;

  void prepare(uint64_t n, int threads, bool need_epoch);
};

// Ring slots used for a run: floor(w_max/delta) + 2, capped by opt.ring_cap.
uint64_t ring_slots(weight_t w_max, const DeltaOptions& opt);

void dijkstra(const CSRGraph& g, vid_t src, std::vector<dist_t>& dist, SsspStats& stats);

void delta_stepping_seq(const CSRGraph& g, vid_t src, const DeltaOptions& opt, DeltaWorkspace& ws,
                        std::vector<dist_t>& dist, SsspStats& stats,
                        std::vector<PhaseRecord>* phase_log = nullptr);

// Uses the OpenMP runtime schedule (omp_set_schedule / OMP_SCHEDULE) for the
// frontier loop.
void delta_stepping_omp(const CSRGraph& g, vid_t src, const DeltaOptions& opt, int threads,
                        DeltaWorkspace& ws, std::vector<dist_t>& dist, SsspStats& stats,
                        std::vector<PhaseRecord>* phase_log = nullptr);

// Shared helpers.
weight_t max_weight(const CSRGraph& g);
const char* to_string(Variant v);
const char* to_string(Filter f);
