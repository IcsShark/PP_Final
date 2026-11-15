// Synthetic graph generator -> binary CSR (.csr).
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <string>

#include "edgelist.hpp"
#include "generators.hpp"
#include "graph.hpp"
#include "timer.hpp"

namespace {

[[noreturn]] void usage(const char* prog, int code) {
  std::fprintf(code ? stderr : stdout,
               "usage: %s kron|urand|grid -o OUT.csr [options]\n"
               "  --scale S          kron/urand: n = 2^S             (default 20)\n"
               "  --degree D         kron/urand: average out-degree  (default 16)\n"
               "  --side L           grid: L x L vertices            (default 2048)\n"
               "  --weights LO,HI    uniform integer weights [LO,HI) (default 1,262144)\n"
               "  --seed S           (default 1)\n"
               "  --emit-wel FILE    also write GAPBS .wel text\n",
               prog);
  std::exit(code);
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 2) usage(argv[0], 2);
    const std::string type = argv[1];
    if (type == "-h" || type == "--help") usage(argv[0], 0);
    std::string out, wel;
    int scale = 20, degree = 16;
    uint64_t side = 2048, seed = 1, lo = 1, hi = 262144;
    for (int i = 2; i < argc; ++i) {
      const std::string k = argv[i];
      auto val = [&]() -> std::string {
        if (i + 1 >= argc) usage(argv[0], 2);
        return argv[++i];
      };
      if (k == "-o") out = val();
      else if (k == "--scale") scale = std::stoi(val());
      else if (k == "--degree") degree = std::stoi(val());
      else if (k == "--side") side = std::stoull(val());
      else if (k == "--seed") seed = std::stoull(val());
      else if (k == "--emit-wel") wel = val();
      else if (k == "--weights") {
        const std::string s = val();
        const size_t c = s.find(',');
        if (c == std::string::npos) usage(argv[0], 2);
        lo = std::stoull(s.substr(0, c));
        hi = std::stoull(s.substr(c + 1));
      } else {
        std::fprintf(stderr, "unknown option: %s\n", k.c_str());
        usage(argv[0], 2);
      }
    }
    if (out.empty()) usage(argv[0], 2);
    if (hi > 0xFFFFFFFFULL + 1 || lo >= hi) throw std::invalid_argument("bad --weights range");

    Timer t;
    std::vector<Edge> edges;
    uint64_t n = 0;
    if (type == "kron") {
      edges = gen_kronecker(scale, degree, seed);
      n = uint64_t{1} << scale;
    } else if (type == "urand") {
      edges = gen_uniform(scale, degree, seed);
      n = uint64_t{1} << scale;
    } else if (type == "grid") {
      edges = gen_grid2d(side);
      n = side * side;
    } else {
      usage(argv[0], 2);
    }
    assign_random_weights(edges, static_cast<weight_t>(lo), static_cast<weight_t>(hi), seed + 7);
    BuildOptions bo;
    bo.symmetrize = true;
    CSRGraph g = build_csr(n, edges, bo);
    edges.clear();
    edges.shrink_to_fit();
    save_csr(g, out);
    std::printf("generated %s %s: n=%llu m=%llu (%.1f s)\n", type.c_str(), out.c_str(), (unsigned long long)g.n,
                (unsigned long long)g.m, t.ms() / 1000);
    if (!wel.empty()) write_wel(g, wel);
    return 0;
  } catch (const std::exception& e) {
    std::fprintf(stderr, "error: %s\n", e.what());
    return 2;
  }
}
