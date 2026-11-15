// Experiment driver: load a .csr graph once, then sweep
//   sources x algorithms x delta x threads x repetitions
// and append one CSV row per run. Timing covers only the SSSP call
// (dist initialisation included, graph loading excluded).
#include <omp.h>

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

#include "graph.hpp"
#include "sssp.hpp"
#include "timer.hpp"

namespace {

struct Args {
  std::string graph;
  std::string algos = "delta-omp";
  std::string deltas = "sweep";
  std::string threads;
  std::string sched = "dynamic,64";
  std::string variant = "all";
  std::string filter = "pop";
  std::string csv;
  std::string phase_log;
  std::string source_list;
  int nsources = 4;
  int reps = 3;
  uint64_t seed = 42;
  uint64_t ring_cap = uint64_t{1} << 19;
  bool verify = false;
  bool quiet = false;
};

[[noreturn]] void usage(const char* prog, int code) {
  std::fprintf(code ? stderr : stdout,
               "usage: %s -g GRAPH.csr [options]\n"
               "  -a, --algo LIST      dijkstra,delta-seq,delta-omp       (default delta-omp)\n"
               "  -d, --delta LIST     'sweep' (2^i * max(w_min,1) up to >= w_max) or values  (default sweep)\n"
               "  -t, --threads LIST   e.g. 1,2,4,6,8,12                  (default omp_get_max_threads)\n"
               "  --variant all|lh     relax all edges / light-heavy split (default all)\n"
               "  --filter pop|merge   where stale entries are removed     (default pop)\n"
               "  --sched KIND[,CHUNK] static|dynamic|guided               (default dynamic,64)\n"
               "  --ring-cap N         max bucket-ring slots per thread    (default 524288)\n"
               "  --sources N          random sources with out-degree > 0  (default 4)\n"
               "  --source LIST        explicit source vertex ids (overrides --sources)\n"
               "  --seed S             RNG seed for source selection       (default 42)\n"
               "  -r, --reps R         repetitions per configuration       (default 3)\n"
               "  --verify             compare every run with Dijkstra\n"
               "  --csv FILE           append one row per run (header written if new)\n"
               "  --phase-log FILE     per-phase records, rep 0 only (sssp_stats build only)\n"
               "  -q, --quiet          only print per-configuration summaries\n",
               prog);
  std::exit(code);
}

std::vector<std::string> split(const std::string& s, char sep = ',') {
  std::vector<std::string> out;
  size_t b = 0;
  while (b <= s.size()) {
    size_t e = s.find(sep, b);
    if (e == std::string::npos) e = s.size();
    if (e > b) out.push_back(s.substr(b, e - b));
    b = e + 1;
  }
  return out;
}

uint64_t to_u64(const std::string& s) {
  size_t pos = 0;
  const unsigned long long v = std::stoull(s, &pos);
  if (pos != s.size()) throw std::invalid_argument("not a number: " + s);
  return v;
}

Args parse(int argc, char** argv) {
  Args a;
  for (int i = 1; i < argc; ++i) {
    const std::string k = argv[i];
    auto val = [&]() -> std::string {
      if (i + 1 >= argc) {
        std::fprintf(stderr, "missing value for %s\n", k.c_str());
        usage(argv[0], 2);
      }
      return argv[++i];
    };
    if (k == "-g" || k == "--graph") a.graph = val();
    else if (k == "-a" || k == "--algo") a.algos = val();
    else if (k == "-d" || k == "--delta") a.deltas = val();
    else if (k == "-t" || k == "--threads") a.threads = val();
    else if (k == "--variant") a.variant = val();
    else if (k == "--filter") a.filter = val();
    else if (k == "--sched") a.sched = val();
    else if (k == "--sources") a.nsources = static_cast<int>(to_u64(val()));
    else if (k == "--source") a.source_list = val();
    else if (k == "--seed") a.seed = to_u64(val());
    else if (k == "--ring-cap") a.ring_cap = to_u64(val());
    else if (k == "-r" || k == "--reps") a.reps = static_cast<int>(to_u64(val()));
    else if (k == "--verify") a.verify = true;
    else if (k == "--csv") a.csv = val();
    else if (k == "--phase-log") a.phase_log = val();
    else if (k == "-q" || k == "--quiet") a.quiet = true;
    else if (k == "-h" || k == "--help") usage(argv[0], 0);
    else {
      std::fprintf(stderr, "unknown option: %s\n", k.c_str());
      usage(argv[0], 2);
    }
  }
  if (a.graph.empty()) usage(argv[0], 2);
  if (a.reps < 1) a.reps = 1;
  return a;
}

void set_schedule(const std::string& spec) {
  const auto parts = split(spec);
  if (parts.empty()) throw std::invalid_argument("empty --sched");
  omp_sched_t kind;
  if (parts[0] == "static") kind = omp_sched_static;
  else if (parts[0] == "dynamic") kind = omp_sched_dynamic;
  else if (parts[0] == "guided") kind = omp_sched_guided;
  else if (parts[0] == "auto") kind = omp_sched_auto;
  else throw std::invalid_argument("unknown schedule kind: " + parts[0]);
  const int chunk = parts.size() > 1 ? static_cast<int>(to_u64(parts[1])) : 0;
  omp_set_schedule(kind, chunk);
}

std::vector<vid_t> pick_sources(const CSRGraph& g, int count, uint64_t seed) {
  std::vector<vid_t> out;
  if (g.n == 0) return out;
  std::mt19937_64 rng(seed);
  std::uniform_int_distribution<uint64_t> U(0, g.n - 1);
  for (uint64_t tries = 0; out.size() < static_cast<size_t>(count) && tries < 1000ULL * count + 1000; ++tries) {
    const vid_t s = static_cast<vid_t>(U(rng));
    if (g.degree(s) == 0 || std::find(out.begin(), out.end(), s) != out.end()) continue;
    out.push_back(s);
  }
  return out;
}

bool file_is_empty(const std::string& path) {
  std::error_code ec;
  return !std::filesystem::exists(path, ec) || std::filesystem::file_size(path, ec) == 0;
}

std::FILE* open_append(const std::string& path, const char* header) {
  if (path.empty()) return nullptr;
  const bool fresh = file_is_empty(path);
  std::FILE* f = std::fopen(path.c_str(), "a");
  if (!f) throw std::runtime_error("cannot open " + path);
  if (fresh) std::fputs(header, f);
  return f;
}

double median(std::vector<double> v) {
  std::sort(v.begin(), v.end());
  const size_t k = v.size();
  return k % 2 ? v[k / 2] : 0.5 * (v[k / 2 - 1] + v[k / 2]);
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Args a = parse(argc, argv);
    set_schedule(a.sched);
    const std::string gname = std::filesystem::path(a.graph).stem().string();
    std::string sched_label = a.sched;  // CSV-safe: "dynamic,64" -> "dynamic:64"
    std::replace(sched_label.begin(), sched_label.end(), ',', ':');

    Timer lt;
    CSRGraph g = load_csr(a.graph);
    const double load_ms = lt.ms();

    const Variant variant = a.variant == "lh" ? Variant::LightHeavy : Variant::AllEdges;
    if (a.variant != "all" && a.variant != "lh") throw std::invalid_argument("--variant must be all or lh");
    const Filter filter = a.filter == "merge" ? Filter::Merge : Filter::Pop;
    if (a.filter != "pop" && a.filter != "merge") throw std::invalid_argument("--filter must be pop or merge");
    if (variant == Variant::LightHeavy && !g.sorted_by_weight) {
      std::fprintf(stderr, "note: sorting adjacency lists by weight for the light/heavy variant\n");
      sort_adjacency_by_weight(g);
    }

    const GraphProfile p = profile_graph(g);
    std::printf("graph %s: n=%llu m=%llu d_avg=%.2f d_max=%llu w=[%u,%u] load=%.1f ms%s\n", gname.c_str(),
                (unsigned long long)p.n, (unsigned long long)p.m, p.d_avg, (unsigned long long)p.d_max, p.w_min,
                p.w_max, load_ms, kStatsEnabled ? "  [STATS BUILD: timings include counters]" : "");

    // Delta list.
    std::vector<dist_t> deltas;
    if (a.deltas == "sweep") {
      const dist_t base = std::max<dist_t>(p.w_min, 1);
      for (dist_t d = base;; d *= 2) {
        deltas.push_back(d);
        if (d >= p.w_max) break;
      }
    } else {
      for (const auto& s : split(a.deltas)) deltas.push_back(to_u64(s));
    }
    for (dist_t d : deltas)
      if (d == 0) throw std::invalid_argument("delta must be >= 1");

    // Thread list.
    std::vector<int> threads;
    if (a.threads.empty()) threads.push_back(omp_get_max_threads());
    else
      for (const auto& s : split(a.threads)) threads.push_back(static_cast<int>(to_u64(s)));

    // Sources.
    std::vector<vid_t> sources;
    if (!a.source_list.empty()) {
      for (const auto& s : split(a.source_list)) {
        const uint64_t v = to_u64(s);
        if (v >= g.n) throw std::invalid_argument("source out of range: " + s);
        sources.push_back(static_cast<vid_t>(v));
      }
    } else {
      sources = pick_sources(g, a.nsources, a.seed);
    }
    if (sources.empty()) throw std::runtime_error("no usable source vertex");
    std::printf("sources:");
    for (vid_t s : sources) std::printf(" %u", s);
    std::printf("\n");

    const auto algos = split(a.algos);
    for (const auto& al : algos)
      if (al != "dijkstra" && al != "delta-seq" && al != "delta-omp")
        throw std::invalid_argument("unknown algorithm: " + al);

    std::FILE* csv = open_append(
        a.csv,
        "graph,algo,variant,filter,sched,threads,delta,source,rep,time_ms,phases,buckets,heavy_passes,"
        "edges_scanned,relax_ok,expansions,stale,merge_dropped,reached,verified,stats_build\n");
    std::FILE* plog = nullptr;
    if (!a.phase_log.empty()) {
      if (!kStatsEnabled) std::fprintf(stderr, "warning: --phase-log needs the sssp_stats build; ignored\n");
      else
        plog = open_append(a.phase_log,
                           "graph,algo,variant,filter,threads,delta,source,phase,bucket,heavy,frontier,expanded,"
                           "edges,max_vertex_edges\n");
    }

    std::vector<dist_t> dist, oracle;
    DeltaWorkspace ws;
    std::vector<PhaseRecord> phases;
    int failures = 0;

    for (vid_t src : sources) {
      if (a.verify) {
        SsspStats tmp;
        dijkstra(g, src, oracle, tmp);
      }
      for (const auto& algo : algos) {
        const bool is_dij = algo == "dijkstra";
        const bool is_seq = algo == "delta-seq";
        const std::vector<dist_t> dlist = is_dij ? std::vector<dist_t>{0} : deltas;
        const std::vector<int> tlist = (is_dij || is_seq) ? std::vector<int>{1} : threads;

        for (dist_t delta : dlist) {
          for (int t : tlist) {
            DeltaOptions o;
            o.delta = delta;
            o.variant = variant;
            o.filter = filter;
            o.w_max = p.w_max;
            o.ring_cap = a.ring_cap;
            std::vector<double> times;
            SsspStats st;
            for (int rep = 0; rep < a.reps; ++rep) {
              std::vector<PhaseRecord>* pl = (plog && rep == 0) ? &phases : nullptr;
              Timer tm;
              if (is_dij) dijkstra(g, src, dist, st);
              else if (is_seq) delta_stepping_seq(g, src, o, ws, dist, st, pl);
              else delta_stepping_omp(g, src, o, t, ws, dist, st, pl);
              const double ms = tm.ms();
              times.push_back(ms);

              uint64_t reached = 0;
              for (dist_t d : dist) reached += (d != INF);
              int verified = -1;
              if (a.verify) {
                verified = 1;
                for (uint64_t v = 0; v < g.n; ++v) {
                  if (dist[v] != oracle[v]) {
                    std::fprintf(stderr,
                                 "MISMATCH algo=%s delta=%llu t=%d src=%u: dist[%llu]=%llu expected %llu\n",
                                 algo.c_str(), (unsigned long long)delta, t, src, (unsigned long long)v,
                                 (unsigned long long)dist[v], (unsigned long long)oracle[v]);
                    verified = 0;
                    ++failures;
                    break;
                  }
                }
              }
              const char* vname = is_dij ? "-" : to_string(variant);
              const char* fname = is_dij ? "-" : to_string(filter);
              if (csv) {
                std::fprintf(csv, "%s,%s,%s,%s,%s,%d,%llu,%u,%d,%.4f,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%d,%d\n",
                             gname.c_str(), algo.c_str(), vname, fname, is_dij || is_seq ? "-" : sched_label.c_str(), t,
                             (unsigned long long)delta, src, rep, ms, (unsigned long long)st.phases,
                             (unsigned long long)st.buckets, (unsigned long long)st.heavy_passes,
                             (unsigned long long)st.edges_scanned, (unsigned long long)st.relax_ok,
                             (unsigned long long)st.expansions, (unsigned long long)st.stale,
                             (unsigned long long)st.merge_dropped, (unsigned long long)reached, verified,
                             kStatsEnabled ? 1 : 0);
                std::fflush(csv);
              }
              if (pl) {
                for (size_t i = 0; i < phases.size(); ++i) {
                  const PhaseRecord& r = phases[i];
                  std::fprintf(plog, "%s,%s,%s,%s,%d,%llu,%u,%zu,%llu,%d,%llu,%llu,%llu,%llu\n", gname.c_str(),
                               algo.c_str(), vname, fname, t, (unsigned long long)delta, src, i,
                               (unsigned long long)r.bucket, r.heavy ? 1 : 0, (unsigned long long)r.frontier,
                               (unsigned long long)r.expanded, (unsigned long long)r.edges,
                               (unsigned long long)r.max_vertex_edges);
                }
                std::fflush(plog);
              }
              if (!a.quiet)
                std::printf("  %-9s delta=%-8llu t=%-2d src=%-9u rep=%d  %10.3f ms  phases=%llu reached=%llu%s\n",
                            algo.c_str(), (unsigned long long)delta, t, src, rep, ms, (unsigned long long)st.phases,
                            (unsigned long long)reached, verified == 1 ? " OK" : verified == 0 ? " WRONG" : "");
            }
            std::printf("%-9s %s/%s delta=%-8llu t=%-2d src=%-9u median=%10.3f ms phases=%llu buckets=%llu\n",
                        algo.c_str(), is_dij ? "-" : to_string(variant), is_dij ? "-" : to_string(filter),
                        (unsigned long long)delta, t, src, median(times), (unsigned long long)st.phases,
                        (unsigned long long)st.buckets);
            std::fflush(stdout);
          }
        }
      }
    }
    if (csv) std::fclose(csv);
    if (plog) std::fclose(plog);
    if (failures) {
      std::fprintf(stderr, "%d run(s) FAILED verification\n", failures);
      return 1;
    }
    if (a.verify) std::printf("all runs verified against Dijkstra\n");
    return 0;
  } catch (const std::exception& e) {
    std::fprintf(stderr, "error: %s\n", e.what());
    return 2;
  }
}
