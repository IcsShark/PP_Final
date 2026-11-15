// Graph Loader: text graph -> binary CSR (.csr), optionally also GAPBS .wel.
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <string>

#include "edgelist.hpp"
#include "graph.hpp"
#include "timer.hpp"

namespace {

[[noreturn]] void usage(const char* prog, int code) {
  std::fprintf(code ? stderr : stdout,
               "usage: %s INPUT -o OUT.csr [options]\n"
               "  --format dimacs|el     input format (default: dimacs if INPUT ends in .gr, else el)\n"
               "                         el = 'u v [w]' per line, '#' or '%%' comments (SNAP, GAPBS .el/.wel)\n"
               "  --one-indexed          el ids start at 1\n"
               "  --symmetrize           add the reverse of every edge (same weight)\n"
               "  --keep-self-loops      default: self loops are removed\n"
               "  --keep-duplicates      default: parallel edges collapse to the min weight\n"
               "  --rand-weights LO,HI   uniform integer weights in [LO, HI) (e.g. 1,262144)\n"
               "  --seed S               seed for --rand-weights (default 1)\n"
               "  --no-sort              do not sort adjacency lists by weight\n"
               "  --emit-wel FILE        also write GAPBS .wel text\n",
               prog);
  std::exit(code);
}

}  // namespace

int main(int argc, char** argv) {
  try {
    std::string in, out, fmt, wel;
    bool one_indexed = false, have_rand = false;
    BuildOptions bo;
    uint64_t lo = 0, hi = 0, seed = 1;
    for (int i = 1; i < argc; ++i) {
      const std::string k = argv[i];
      auto val = [&]() -> std::string {
        if (i + 1 >= argc) usage(argv[0], 2);
        return argv[++i];
      };
      if (k == "-o") out = val();
      else if (k == "--format") fmt = val();
      else if (k == "--one-indexed") one_indexed = true;
      else if (k == "--symmetrize") bo.symmetrize = true;
      else if (k == "--keep-self-loops") bo.remove_self_loops = false;
      else if (k == "--keep-duplicates") bo.dedup = false;
      else if (k == "--no-sort") bo.sort_by_weight = false;
      else if (k == "--seed") seed = std::stoull(val());
      else if (k == "--emit-wel") wel = val();
      else if (k == "--rand-weights") {
        const std::string s = val();
        const size_t c = s.find(',');
        if (c == std::string::npos) usage(argv[0], 2);
        lo = std::stoull(s.substr(0, c));
        hi = std::stoull(s.substr(c + 1));
        have_rand = true;
      } else if (k == "-h" || k == "--help") usage(argv[0], 0);
      else if (!k.empty() && k[0] == '-') {
        std::fprintf(stderr, "unknown option: %s\n", k.c_str());
        usage(argv[0], 2);
      } else in = k;
    }
    if (in.empty() || out.empty()) usage(argv[0], 2);
    if (fmt.empty()) fmt = (in.size() > 3 && in.substr(in.size() - 3) == ".gr") ? "dimacs" : "el";

    Timer t;
    EdgeListData d = fmt == "dimacs" ? read_dimacs(in) : read_edge_list(in, one_indexed);
    std::printf("read %s: n=%llu input edges=%zu (%.1f s)\n", in.c_str(), (unsigned long long)d.n, d.edges.size(),
                t.ms() / 1000);
    if (have_rand) {
      if (hi > 0xFFFFFFFFULL + 1 || lo >= hi) throw std::invalid_argument("bad --rand-weights range");
      assign_random_weights(d.edges, static_cast<weight_t>(lo), static_cast<weight_t>(hi), seed);
    } else if (!d.has_weights) {
      throw std::runtime_error("input has no weights; pass --rand-weights LO,HI");
    }

    t.reset();
    CSRGraph g = build_csr(d.n, d.edges, bo);
    d.edges.clear();
    d.edges.shrink_to_fit();
    std::printf("built CSR: n=%llu m=%llu (%.1f s)\n", (unsigned long long)g.n, (unsigned long long)g.m,
                t.ms() / 1000);

    t.reset();
    save_csr(g, out);
    std::printf("wrote %s (%.1f s)\n", out.c_str(), t.ms() / 1000);
    if (!wel.empty()) {
      t.reset();
      write_wel(g, wel);
      std::printf("wrote %s (%.1f s)\n", wel.c_str(), t.ms() / 1000);
    }
    const GraphProfile p = profile_graph(g);
    std::printf("profile: d_avg=%.2f d_max=%llu w_min=%u w_max=%u zero_out_degree=%llu\n", p.d_avg,
                (unsigned long long)p.d_max, p.w_min, p.w_max, (unsigned long long)p.zero_out_degree);
    return 0;
  } catch (const std::exception& e) {
    std::fprintf(stderr, "error: %s\n", e.what());
    return 2;
  }
}
