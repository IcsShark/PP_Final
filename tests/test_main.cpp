// Correctness tests.
//
// 1. Testcase files: every tests/testcase/<name>.in.txt (format: see
//    tests/gen_testcases.py) is solved by Dijkstra, delta-seq and delta-omp
//    over many deltas, both variants, both filters, several thread counts and
//    two ring capacities (default, and a tiny one that forces the overflow
//    path). Every result is compared with <name>.ans.txt.
// 2. Unit tests for the I/O and CSR code, the bucket ring, and (stats build
//    only) the work counters.
//
// usage: test_sssp [TESTCASE_DIR]     (default tests/testcase)
// Exit code 0 = all passed.
#include <omp.h>

#include <algorithm>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "edgelist.hpp"
#include "generators.hpp"
#include "graph.hpp"
#include "sssp.hpp"

namespace fs = std::filesystem;

namespace {

int g_fail = 0, g_checks = 0;

#define CHECK(cond)                                                                          \
  do {                                                                                       \
    ++g_checks;                                                                              \
    if (!(cond)) {                                                                           \
      ++g_fail;                                                                              \
      if (g_fail <= 50) std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
    }                                                                                        \
  } while (0)

constexpr uint64_t kTinyRingCap = 3;  // forces most insertions through RingBins::overflow

// ------------------------------------------------------------ testcase files

struct TestCase {
  uint64_t n = 0;
  vid_t src = 0;           // 0-indexed
  std::vector<Edge> edges;  // 0-indexed
  std::vector<dist_t> expected;
  bool has_expected = false;
};

// Reads "<name>.in.txt" (+ optional "<name>.ans.txt"); vertex ids 1..n in the file.
std::vector<TestCase> read_testcase_file(const fs::path& in_path) {
  std::ifstream in(in_path);
  if (!in) throw std::runtime_error("cannot open " + in_path.string());
  std::vector<TestCase> cases;
  int T = 0;
  in >> T;
  for (int t = 0; t < T; ++t) {
    TestCase c;
    uint64_t m, s;
    if (!(in >> c.n >> m >> s)) throw std::runtime_error("bad header in " + in_path.string());
    if (s < 1 || s > c.n) throw std::runtime_error("bad source in " + in_path.string());
    c.src = static_cast<vid_t>(s - 1);
    c.edges.resize(m);
    for (Edge& e : c.edges) {
      uint64_t u, v, w;
      if (!(in >> u >> v >> w)) throw std::runtime_error("truncated " + in_path.string());
      if (u < 1 || v < 1 || u > c.n || v > c.n || w > 0xFFFFFFFFULL)
        throw std::runtime_error("bad edge in " + in_path.string());
      e = {static_cast<vid_t>(u - 1), static_cast<vid_t>(v - 1), static_cast<weight_t>(w)};
    }
    cases.push_back(std::move(c));
  }

  std::string name = in_path.filename().string();
  name = name.substr(0, name.size() - std::string(".in.txt").size());
  std::ifstream ans(in_path.parent_path() / (name + ".ans.txt"));
  if (ans) {
    std::string line;
    for (TestCase& c : cases) {
      if (!std::getline(ans, line)) throw std::runtime_error("answer file too short for " + name);
      std::istringstream ls(line);
      long long d;
      while (ls >> d) c.expected.push_back(d < 0 ? INF : static_cast<dist_t>(d));
      if (c.expected.size() != c.n) throw std::runtime_error("answer length mismatch in " + name);
      c.has_expected = true;
    }
  }
  return cases;
}

// Deltas tried on one graph: tiny values, a x8 sweep over the weight range,
// and one value larger than every edge (Bellman-Ford-like end).
std::vector<dist_t> deltas_for(const GraphProfile& p) {
  std::vector<dist_t> d = {1, 2, 3, 7};
  for (dist_t x = std::max<dist_t>(p.w_min, 1);; x *= 8) {
    d.push_back(x);
    if (x >= p.w_max) break;
  }
  d.push_back(static_cast<dist_t>(p.w_max) * 10 + 1);
  std::sort(d.begin(), d.end());
  d.erase(std::unique(d.begin(), d.end()), d.end());
  return d;
}

// Runs every sequential/parallel configuration and compares with `expected`.
void check_all_algorithms(const CSRGraph& g, vid_t src, const std::vector<dist_t>& expected,
                          const std::vector<dist_t>& deltas, const std::string& label) {
  const weight_t wmax = max_weight(g);
  DeltaWorkspace ws;
  std::vector<dist_t> dist;
  SsspStats st, st_seq;

  auto report = [&](bool ok, const char* algo, dist_t delta, int t, Variant var, Filter fil, uint64_t cap) {
    CHECK(ok);
    if (!ok)
      std::fprintf(stderr, "  [%s] %s delta=%llu t=%d %s/%s ring_cap=%llu\n", label.c_str(), algo,
                   (unsigned long long)delta, t, to_string(var), to_string(fil), (unsigned long long)cap);
  };

  for (uint64_t cap : {DeltaOptions{}.ring_cap, kTinyRingCap}) {
    const bool tiny = cap == kTinyRingCap;
    for (dist_t delta : deltas) {
      for (Variant var : {Variant::AllEdges, Variant::LightHeavy}) {
        for (Filter fil : {Filter::Pop, Filter::Merge}) {
          DeltaOptions o;
          o.delta = delta;
          o.variant = var;
          o.filter = fil;
          o.w_max = wmax;
          o.ring_cap = cap;
          delta_stepping_seq(g, src, o, ws, dist, st_seq);
          report(dist == expected, "delta-seq", delta, 1, var, fil, cap);

          const std::vector<int> threads = tiny ? std::vector<int>{1, 3} : std::vector<int>{1, 2, 3, 4, 8};
          for (int t : threads) {
            delta_stepping_omp(g, src, o, t, ws, dist, st);
            report(dist == expected, "delta-omp", delta, t, var, fil, cap);
            if (t == 1) {
              // One thread must follow exactly the same bucket/phase sequence.
              CHECK(st.phases == st_seq.phases);
              CHECK(st.buckets == st_seq.buckets);
              CHECK(st.heavy_passes == st_seq.heavy_passes);
            }
          }
        }
      }
    }
  }
}

int run_testcase_dir(const fs::path& dir) {
  if (!fs::is_directory(dir)) {
    std::fprintf(stderr, "FAIL: testcase directory %s not found (run from the repo root)\n", dir.string().c_str());
    ++g_fail;
    return 0;
  }
  std::vector<fs::path> files;
  for (const auto& e : fs::directory_iterator(dir)) {
    const std::string f = e.path().filename().string();
    if (f.size() > 7 && f.compare(f.size() - 7, 7, ".in.txt") == 0) files.push_back(e.path());
  }
  std::sort(files.begin(), files.end());
  int total = 0;
  for (const fs::path& f : files) {
    const int fail_before = g_fail;
    const auto cases = read_testcase_file(f);
    for (size_t i = 0; i < cases.size(); ++i) {
      const TestCase& c = cases[i];
      const std::string label = f.filename().string() + "#" + std::to_string(i + 1);
      CSRGraph g = build_csr(c.n, c.edges, BuildOptions{});

      std::vector<dist_t> oracle;
      SsspStats st;
      dijkstra(g, c.src, oracle, st);
      if (c.has_expected) {
        const bool ok = oracle == c.expected;
        CHECK(ok);
        if (!ok) std::fprintf(stderr, "  [%s] Dijkstra disagrees with the .ans file\n", label.c_str());
      }
      const std::vector<dist_t>& expected = c.has_expected ? c.expected : oracle;
      check_all_algorithms(g, c.src, expected, deltas_for(profile_graph(g)), label);
    }
    total += static_cast<int>(cases.size());
    std::printf("  %-22s %3zu tests  %s%s\n", f.filename().string().c_str(), cases.size(),
                g_fail == fail_before ? "ok" : "FAILED",
                cases.empty() || cases[0].has_expected ? "" : "  (no .ans.txt: checked against Dijkstra only)");
    std::fflush(stdout);
  }
  return total;
}

// ------------------------------------------------------------ unit tests

void test_dedup_and_self_loops() {
  std::vector<Edge> e = {{0, 1, 5}, {0, 1, 3}, {0, 0, 1}, {1, 2, 2}, {1, 2, 9}};
  CSRGraph g = build_csr(3, e, BuildOptions{});
  CHECK(g.m == 2);
  CHECK(g.degree(0) == 1);
  CHECK(g.wt[g.offsets[0]] == 3);
  BuildOptions keep;
  keep.dedup = false;
  keep.remove_self_loops = false;
  CSRGraph g2 = build_csr(3, e, keep);
  CHECK(g2.m == 5);
}

void test_sorted_adjacency() {
  std::vector<Edge> e = {{0, 1, 9}, {0, 2, 1}, {0, 3, 5}, {0, 4, 5}};
  CSRGraph g = build_csr(5, e, BuildOptions{});
  CHECK(g.sorted_by_weight);
  bool sorted = true;
  for (eid_t i = g.offsets[0] + 1; i < g.offsets[1]; ++i) sorted &= g.wt[i - 1] <= g.wt[i];
  CHECK(sorted);
}

std::string tmp_path(const std::string& name) {
  return (fs::temp_directory_path() / ("sssp_test_" + name)).string();
}

void write_file(const std::string& path, const std::string& text) {
  std::ofstream f(path, std::ios::binary);
  f << text;
}

void test_dimacs_parse() {
  const std::string path = tmp_path("small.gr");
  write_file(path, "c tiny DIMACS file\np sp 3 3\na 1 2 5\na 2 3 7\na 1 3 20\n");
  EdgeListData d = read_dimacs(path);
  CHECK(d.n == 3);
  CHECK(d.edges.size() == 3);
  CSRGraph g = build_csr(d.n, d.edges, BuildOptions{});
  std::vector<dist_t> dist;
  SsspStats st;
  dijkstra(g, 0, dist, st);
  CHECK((dist == std::vector<dist_t>{0, 5, 12}));
  fs::remove(path);
}

void test_edge_list_parse() {
  const std::string path = tmp_path("small.el");
  write_file(path, "# comment\n% another\n0 1\r\n1\t2\n\n");
  EdgeListData d = read_edge_list(path, false);
  CHECK(d.n == 3);
  CHECK(!d.has_weights);
  assign_random_weights(d.edges, 3, 4, 1);  // all weights 3
  BuildOptions bo;
  bo.symmetrize = true;
  CSRGraph g = build_csr(d.n, d.edges, bo);
  CHECK(g.m == 4);
  std::vector<dist_t> dist;
  SsspStats st;
  dijkstra(g, 2, dist, st);
  CHECK((dist == std::vector<dist_t>{6, 3, 0}));

  write_file(path, "1 2 7\n2 3 8\n");
  EdgeListData w = read_edge_list(path, true);
  CHECK(w.has_weights);
  CHECK(w.n == 3);
  CHECK(w.edges[1].u == 1 && w.edges[1].v == 2 && w.edges[1].w == 8);
  fs::remove(path);
}

void test_csr_roundtrip() {
  auto e = gen_uniform(10, 8, 3);
  assign_random_weights(e, 1, 100, 4);
  BuildOptions bo;
  bo.symmetrize = true;
  CSRGraph g = build_csr(1 << 10, e, bo);
  const std::string path = tmp_path("rt.csr");
  save_csr(g, path);
  CSRGraph h = load_csr(path);
  CHECK(h.n == g.n && h.m == g.m && h.sorted_by_weight == g.sorted_by_weight);
  CHECK(h.offsets == g.offsets && h.dst == g.dst && h.wt == g.wt);
  fs::remove(path);
}

void test_ring_bins() {
  RingBins b;
  b.prepare(4);  // window [0, 4)
  b.push(2, 20);
  b.push(9, 90);    // overflow
  b.push(100, 7);   // overflow
  b.push(0, 1);
  CHECK(b.next(0) == 0);
  b.taken(0);
  b.slot(0).clear();
  CHECK(b.next(0) == 2);
  b.advance(2);
  b.taken(2);
  b.slot(2).clear();
  CHECK(b.next(2) == 9);  // only overflow left
  b.advance(9);           // window [9, 13): 9 moves into the ring, 100 stays
  CHECK(b.overflow.size() == 1);
  CHECK(b.slot(9).size() == 1 && b.slot(9)[0] == 90);
  b.push(12, 5);  // last slot of the window, wraps to slot 0
  b.taken(9);
  b.slot(9).clear();
  CHECK(b.next(9) == 12);
  b.advance(12);
  b.taken(12);
  b.slot(12).clear();
  CHECK(b.next(12) == 100);
  b.advance(100);
  b.taken(100);
  b.slot(100).clear();
  CHECK(b.empty());
  CHECK(b.next(100) == NO_BUCKET);

  // Bitmap search across many words, including wrap-around.
  RingBins r;
  r.prepare(1000);
  r.advance(950);
  r.push(1940, 1);  // slot 940
  r.push(1003, 2);  // slot 3 (wrapped)
  CHECK(r.next(950) == 1003);
}

// Work invariants that only the stats build can check.
void test_stats_invariants() {
  if constexpr (!kStatsEnabled) return;
  // With delta = 1 and w_min >= 1, bucket index == exact distance, so every
  // reached vertex is expanded exactly once (no re-expansion is possible).
  auto e = gen_kronecker(10, 8, 5);
  assign_random_weights(e, 1, 50, 6);
  BuildOptions bo;
  bo.symmetrize = true;
  CSRGraph g = build_csr(1 << 10, e, bo);
  DeltaWorkspace ws;
  std::vector<dist_t> dist;
  SsspStats st;
  vid_t src = 0;
  while (g.degree(src) == 0) ++src;

  auto reached = [&] {
    uint64_t r = 0;
    for (dist_t d : dist) r += d != INF;
    return r;
  };
  dijkstra(g, src, dist, st);
  CHECK(st.expansions == reached());

  for (uint64_t cap : {DeltaOptions{}.ring_cap, kTinyRingCap}) {
    for (Variant var : {Variant::AllEdges, Variant::LightHeavy}) {
      DeltaOptions o;
      o.delta = 1;
      o.variant = var;
      o.ring_cap = cap;
      delta_stepping_seq(g, src, o, ws, dist, st);
      CHECK(st.expansions == reached());
      for (int t : {1, 4}) {
        delta_stepping_omp(g, src, o, t, ws, dist, st);
        CHECK(st.expansions == reached());
      }
    }
  }

  // Phase log is consistent with the totals.
  DeltaOptions o;
  o.delta = 64;
  std::vector<PhaseRecord> log;
  delta_stepping_omp(g, src, o, 4, ws, dist, st, &log);
  CHECK(log.size() == st.phases);
  uint64_t edges = 0, exp = 0;
  for (const PhaseRecord& r : log) {
    edges += r.edges;
    exp += r.expanded;
  }
  CHECK(edges == st.edges_scanned);
  CHECK(exp == st.expansions);

  // Per-thread imbalance fields: edges/T <= max_thread_edges <= edges,
  // max_thread_edges >= max_vertex_edges (one vertex is done by one thread),
  // and 0 <= mean_wait <= max_wait.
  bool bounds_ok = true, waits_ok = true;
  for (const PhaseRecord& r : log) {
    bounds_ok &= r.max_thread_edges <= r.edges;
    bounds_ok &= r.max_thread_edges * 4 >= r.edges;
    bounds_ok &= r.max_thread_edges >= r.max_vertex_edges;
    waits_ok &= r.mean_wait_s >= 0 && r.mean_wait_s <= r.max_wait_s + 1e-12;
  }
  CHECK(bounds_ok);
  CHECK(waits_ok);

  // Sequential: one thread does everything, so max_thread_edges == edges.
  delta_stepping_seq(g, src, o, ws, dist, st, &log);
  bool seq_ok = !log.empty();
  for (const PhaseRecord& r : log) seq_ok &= r.max_thread_edges == r.edges && r.max_wait_s == 0;
  CHECK(seq_ok);
}

}  // namespace

int main(int argc, char** argv) {
  const fs::path dir = argc > 1 ? argv[1] : "tests/testcase";
  std::printf("running tests (%s build, omp max threads = %d)\n", kStatsEnabled ? "stats" : "timing",
              omp_get_max_threads());
  try {
    test_dedup_and_self_loops();
    test_sorted_adjacency();
    test_dimacs_parse();
    test_edge_list_parse();
    test_csr_roundtrip();
    test_ring_bins();
    test_stats_invariants();
    std::printf("  unit tests             %s\n", g_fail ? "FAILED" : "ok");
    const int n = run_testcase_dir(dir);
    std::printf("  %d testcases from %s\n", n, dir.string().c_str());
  } catch (const std::exception& e) {
    std::fprintf(stderr, "FAIL: exception: %s\n", e.what());
    ++g_fail;
  }
  if (g_fail) {
    std::printf("FAILED: %d of %d checks\n", g_fail, g_checks);
    return 1;
  }
  std::printf("PASSED: %d checks\n", g_checks);
  return 0;
}
