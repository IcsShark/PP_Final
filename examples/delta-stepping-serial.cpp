/**
 * @file 
 * @author Gino (penguin71630.cs11@nycu.edu.tw)
 * @brief Delta-stepping algorithm (Serial) on directed graph, weights of every edge are non-negative.
 *
 * @see U. Meyer and P. Sanders, "Delta-stepping: a parallelizable shortest path algorithm," 
 *      Journal of Algorithms, vol. 49, no. 1, pp. 114-152, 2003.
 */

#include <bits/stdc++.h>
using namespace std;

using ll = long long;

static const ll LINF = 4e18;


//#define SHOW_METRICS

#ifdef SHOW_METRICS
#define METRIC(stmt) stmt
#else
#define METRIC(stmt)
#endif


int main(int argc, char *argv[]) {
  int _input_delta;
  if (argc < 2) return cerr << "Usage: ./a.out {Delta} < input_file" << endl, 1;
  try {
    _input_delta = stoi(argv[1]);
  } catch (const std::invalid_argument& e) {
    return cerr << "Usage: ./a.out {Delta} < input_file" << endl, 1;
  } catch (const std::out_of_range& e) {
    return cerr << "Usage: ./a.out {Delta} < input_file" << endl, 1;
  }
  if (_input_delta < 1) return cerr << "Usage: ./a.out {Delta} < input_file" << endl, 1;



  int TEST; cin >> TEST; for (int test_id = 1; test_id <= TEST; test_id++) {
    /* ============== Algorithm Inputs ============== */
    int Delta;                        // Δ
    int n, m, s;                      // number of vertices, number of edges, starting vertex
    vector<vector<pair<int, ll>>> G;  // G[u] := {v1, w1}, {v2, w2}, ...
    vector<ll> dis;                   // dis[u] := shortest distance from s to u
    /* ============================================== */


#ifdef SHOW_METRICS
    /* =================== Metrics ================== */
    // Metrics related to graph itself, not performance
    int num_reached_vertices = 0;

    // Metrics related to performance
    ll num_edges_scanned = 0;  // total number of edge visits (an edge visited k times counts k times)
    ll num_relax_success = 0;  // number of successful "dis[v] = dis[u] + w"
    ll num_expansions    = 0;  // number of vertices expanded (popped and not stale)
    ll num_phases        = 0;  // number of phases (= barriers in the parallel version)
    ll num_buckets       = 0;  // number of distinct buckets processed
    ll max_phase_edges   = 0;  // max number of edges scanned within a single phase
    ll num_empty_phases  = 0;  // phases where every popped vertex was stale (no real work)
    ll last_qd           = -1; // bucket index of the previous phase
    /* ============================================== */
#endif

    Delta = _input_delta;

    cin >> n >> m >> s;
    G.resize(n + 1);
    for (int i = 0; i < m; i++) {
      int u, v; ll w; cin >> u >> v >> w;
      G[u].push_back({v, w});
    }
    dis.resize(n + 1, LINF);

    /* ========== Delta Stepping Algorithm ========== */

    map<ll, vector<int>> bucket;  // bucket[qd]: {u | (dis[u] / Delta) == qd}
    bucket[0].push_back(s);
    dis[s] = 0;

    while (!bucket.empty()) {
      ll qd = bucket.begin()->first;
      vector<int> us = move(bucket.begin()->second);
      bucket.erase(bucket.begin());
      int n_this_round = us.size();

      METRIC(num_phases++);
      METRIC(if (qd != last_qd) { num_buckets++; last_qd = qd; });
      METRIC(ll phase_edges = 0);
      METRIC(ll phase_expansions = 0);

      for (int i = 0; i < n_this_round; i++) {
        int u = us[i];
        if (qd > dis[u] / Delta) continue;
        METRIC(num_expansions++);
        METRIC(phase_expansions++);
        METRIC(phase_edges += G[u].size());
        for (auto& [v, w] : G[u]) {
          if (dis[v] > dis[u] + w) {
            dis[v] = dis[u] + w;
            bucket[dis[v] / Delta].push_back(v);
            METRIC(num_relax_success++);
          }
        }
      }

      METRIC(num_edges_scanned += phase_edges);
      METRIC(max_phase_edges = max(max_phase_edges, phase_edges));
      METRIC(num_empty_phases += (phase_expansions == 0));
    }

    /* ============================================== */

    for (int u = 1; u <= n; u++)
      cout << (dis[u] != LINF ? dis[u] : -1) << " \n"[u == n];

#ifdef SHOW_METRICS
    /* ================ Print Metrics =============== */
    for (int u = 1; u <= n; u++) num_reached_vertices += (dis[u] != LINF);

    // One line per test case, "key=value" separated by spaces, easy to parse into CSV.
    cerr << fixed << setprecision(3)
         << "test="             << test_id
         << " delta="           << Delta
         << " n="               << n
         << " m="               << m
         << " reached="         << num_reached_vertices
         << " edges_scanned="   << num_edges_scanned
         << " relax_success="   << num_relax_success
         << " expansions="      << num_expansions
         << " stale_skips="     << (num_relax_success + 1 - num_expansions)
         << " phases="          << num_phases
         << " buckets="         << num_buckets
         << " empty_phases="    << num_empty_phases
         << " max_phase_edges=" << max_phase_edges
         // derived ratios
         << " reinsert_ratio="  << (double)num_expansions / max(1, num_reached_vertices)  // Dijkstra = 1
         << " phases_per_bucket=" << (double)num_phases / max(1LL, num_buckets)
         << " avg_parallelism=" << (double)num_edges_scanned / max(1LL, num_phases)     // edges per phase
         << endl;
    /* ============================================== */
#endif
  }

  return 0;
}
