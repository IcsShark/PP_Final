#include "edgelist.hpp"

#include <cstdio>
#include <algorithm>
#include <cstring>
#include <random>
#include <stdexcept>
#include <string_view>

namespace {

// Buffered line reader: much faster than std::getline for 100M+ line files.
class LineReader {
 public:
  explicit LineReader(const std::string& path) : f_(std::fopen(path.c_str(), "rb")), buf_(1 << 24) {
    if (!f_) throw std::runtime_error("cannot open: " + path);
  }
  ~LineReader() {
    if (f_) std::fclose(f_);
  }
  LineReader(const LineReader&) = delete;
  LineReader& operator=(const LineReader&) = delete;

  bool next(std::string_view& line) {
    while (true) {
      char* base = buf_.data();
      if (pos_ < len_) {
        const char* nl = static_cast<const char*>(std::memchr(base + pos_, '\n', len_ - pos_));
        if (nl) {
          line = std::string_view(base + pos_, static_cast<size_t>(nl - (base + pos_)));
          pos_ = static_cast<size_t>(nl - base) + 1;
          return true;
        }
      }
      if (eof_) {
        if (pos_ < len_) {
          line = std::string_view(base + pos_, len_ - pos_);
          pos_ = len_;
          return true;
        }
        return false;
      }
      const size_t rem = len_ - pos_;
      std::memmove(base, base + pos_, rem);
      pos_ = 0;
      len_ = rem;
      if (len_ == buf_.size()) throw std::runtime_error("line too long");
      const size_t got = std::fread(base + len_, 1, buf_.size() - len_, f_);
      len_ += got;
      if (got == 0) eof_ = true;
    }
  }

 private:
  std::FILE* f_;
  std::vector<char> buf_;
  size_t pos_ = 0, len_ = 0;
  bool eof_ = false;
};

bool next_uint(std::string_view s, size_t& p, uint64_t& out) {
  while (p < s.size() && (s[p] == ' ' || s[p] == '\t' || s[p] == '\r' || s[p] == ',')) ++p;
  if (p >= s.size() || s[p] < '0' || s[p] > '9') return false;
  uint64_t x = 0;
  while (p < s.size() && s[p] >= '0' && s[p] <= '9') {
    x = x * 10 + static_cast<uint64_t>(s[p] - '0');
    ++p;
  }
  out = x;
  return true;
}

weight_t checked_weight(uint64_t w) {
  if (w > std::numeric_limits<weight_t>::max()) throw std::runtime_error("edge weight exceeds 32 bits");
  return static_cast<weight_t>(w);
}

}  // namespace

EdgeListData read_dimacs(const std::string& path) {
  LineReader r(path);
  EdgeListData d;
  d.has_weights = true;
  bool have_header = false;
  std::string_view line;
  uint64_t lineno = 0;
  while (r.next(line)) {
    ++lineno;
    if (line.empty() || line[0] == 'c') continue;
    size_t p = 1;
    if (line[0] == 'p') {
      // "p sp <n> <m>"
      while (p < line.size() && (line[p] < '0' || line[p] > '9')) ++p;
      uint64_t n = 0, m = 0;
      if (!next_uint(line, p, n) || !next_uint(line, p, m))
        throw std::runtime_error("bad DIMACS header at line " + std::to_string(lineno));
      d.n = n;
      d.edges.reserve(m);
      have_header = true;
    } else if (line[0] == 'a') {
      uint64_t u, v, w;
      if (!next_uint(line, p, u) || !next_uint(line, p, v) || !next_uint(line, p, w))
        throw std::runtime_error("bad DIMACS arc at line " + std::to_string(lineno));
      if (!have_header) throw std::runtime_error("DIMACS arc before 'p' line");
      if (u == 0 || v == 0 || u > d.n || v > d.n)
        throw std::runtime_error("DIMACS vertex out of range at line " + std::to_string(lineno));
      d.edges.push_back({static_cast<vid_t>(u - 1), static_cast<vid_t>(v - 1), checked_weight(w)});
    }
  }
  if (!have_header) throw std::runtime_error("no DIMACS 'p' line in " + path);
  return d;
}

EdgeListData read_edge_list(const std::string& path, bool one_indexed) {
  LineReader r(path);
  EdgeListData d;
  std::string_view line;
  uint64_t lineno = 0, max_id = 0;
  bool first = true;
  while (r.next(line)) {
    ++lineno;
    size_t p = 0;
    while (p < line.size() && (line[p] == ' ' || line[p] == '\t' || line[p] == '\r')) ++p;
    if (p >= line.size() || line[p] == '#' || line[p] == '%') continue;
    uint64_t u, v, w = 0;
    if (!next_uint(line, p, u) || !next_uint(line, p, v))
      throw std::runtime_error("bad edge at line " + std::to_string(lineno));
    const bool has_w = next_uint(line, p, w);
    if (first) {
      d.has_weights = has_w;
      first = false;
    } else if (d.has_weights && !has_w) {
      throw std::runtime_error("missing weight at line " + std::to_string(lineno));
    }
    if (one_indexed) {
      if (u == 0 || v == 0) throw std::runtime_error("id 0 in one-indexed input at line " + std::to_string(lineno));
      --u;
      --v;
    }
    if (u >= (uint64_t{1} << 32) - 1 || v >= (uint64_t{1} << 32) - 1) throw std::runtime_error("vertex id too large");
    max_id = std::max({max_id, u, v});
    d.edges.push_back({static_cast<vid_t>(u), static_cast<vid_t>(v), d.has_weights ? checked_weight(w) : 0});
  }
  d.n = d.edges.empty() ? 0 : max_id + 1;
  return d;
}

void assign_random_weights(std::vector<Edge>& edges, weight_t lo, weight_t hi_exclusive, uint64_t seed) {
  if (hi_exclusive <= lo) throw std::invalid_argument("random weight range is empty");
  std::mt19937_64 rng(seed);
  std::uniform_int_distribution<uint64_t> dist(lo, static_cast<uint64_t>(hi_exclusive) - 1);
  for (Edge& e : edges) e.w = static_cast<weight_t>(dist(rng));
}

void write_wel(const CSRGraph& g, const std::string& path) {
  std::FILE* f = std::fopen(path.c_str(), "wb");
  if (!f) throw std::runtime_error("cannot open for writing: " + path);
  std::vector<char> buf(1 << 24);
  size_t len = 0;
  auto flush = [&] {
    if (len && std::fwrite(buf.data(), 1, len, f) != len) throw std::runtime_error("write failed: " + path);
    len = 0;
  };
  auto put_uint = [&](uint64_t x, char sep) {
    char tmp[24];
    int k = 0;
    do {
      tmp[k++] = static_cast<char>('0' + x % 10);
      x /= 10;
    } while (x);
    while (k) buf[len++] = tmp[--k];
    buf[len++] = sep;
  };
  for (uint64_t u = 0; u < g.n; ++u) {
    for (eid_t i = g.offsets[u]; i < g.offsets[u + 1]; ++i) {
      if (len + 80 > buf.size()) flush();
      put_uint(u, ' ');
      put_uint(g.dst[i], ' ');
      put_uint(g.wt[i], '\n');
    }
  }
  flush();
  if (std::fclose(f) != 0) throw std::runtime_error("close failed: " + path);
}
