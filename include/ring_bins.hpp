#pragma once
#include <algorithm>
#include <bit>
#include <stdexcept>
#include <utility>
#include <vector>

#include "types.hpp"

// Bucket storage owned by one thread: a circular window of C slots plus an
// overflow list.
//
// Window. Buckets in [base, base + C) live in ring[b % C]. `base` is the
// bucket currently being processed (set by advance()). While bucket `cur` is
// processed, every insertion lands in [cur, cur + floor(w_max/delta) + 1], so
// with C = floor(w_max/delta) + 2 everything fits in the ring and the overflow
// list is never touched (the normal case for the real datasets).
//
// Overflow. C is capped (DeltaOptions::ring_cap) so memory stays bounded when
// w_max/delta is huge (e.g. weights ~1e9 with delta = 1 would otherwise need
// ~1e9 slots). Insertions at or beyond base + C go to `overflow`, and
// advance() moves them into the ring once the window reaches them.
//
// Occupancy bitmap. Bit s of `occ` is set iff ring[s] is non-empty, so next()
// skips 64 empty slots per word instead of probing them one by one (matters
// for small delta, where most slots are empty).
struct RingBins {
  std::vector<std::vector<vid_t>> ring;
  std::vector<uint64_t> occ;  // occupancy bitmap, C bits
  uint64_t C = 0;             // number of slots
  uint64_t base = 0;          // window is [base, base + C)
  uint64_t in_ring = 0;       // entries stored in the ring (incl. stale ones)
  std::vector<std::pair<uint64_t, vid_t>> overflow;  // (bucket, vertex)
  uint64_t ovf_min = NO_BUCKET;

  void prepare(uint64_t slots) {
    if (!empty()) throw std::logic_error("RingBins::prepare on non-empty bins");
    if (slots == 0) throw std::invalid_argument("RingBins needs at least one slot");
    if (C != slots) {
      ring.assign(slots, {});
      occ.assign((slots + 63) / 64, 0);
      C = slots;
    }
    base = 0;
    ovf_min = NO_BUCKET;
  }

  bool empty() const { return in_ring == 0 && overflow.empty(); }

  // Precondition: bucket >= base.
  void push(uint64_t bucket, vid_t v) {
    if (bucket - base < C) {
      const uint64_t s = bucket % C;
      ring[s].push_back(v);
      occ[s >> 6] |= uint64_t{1} << (s & 63);
      ++in_ring;
    } else {
      overflow.emplace_back(bucket, v);
      if (bucket < ovf_min) ovf_min = bucket;
    }
  }

  // Smallest non-empty bucket index >= cur (ring or overflow), or NO_BUCKET.
  // Precondition: base <= cur and no entry is stored below cur.
  uint64_t next(uint64_t cur) const {
    uint64_t r = NO_BUCKET;
    if (in_ring) {
      // Every ring entry is in [cur, base + C) with base <= cur, so the first
      // occupied slot in circular order starting at cur % C is the minimum.
      const uint64_t p = cur % C;
      const size_t nw = occ.size();
      size_t w = p >> 6;
      uint64_t word = occ[w] & (~uint64_t{0} << (p & 63));
      for (size_t k = 0; k <= nw; ++k) {
        if (word) {
          const uint64_t pos = (static_cast<uint64_t>(w) << 6) + static_cast<uint64_t>(std::countr_zero(word));
          r = cur + (pos + C - p) % C;
          break;
        }
        w = (w + 1 == nw) ? 0 : w + 1;
        word = occ[w];
      }
    }
    return std::min(r, ovf_min);
  }

  // Slide the window to start at bucket b. Precondition: no entry (ring or
  // overflow) is below b, i.e. b is the global minimum returned by next().
  void advance(uint64_t b) {
    base = b;
    if (ovf_min - b >= C) return;  // nothing in overflow reaches the window
    size_t keep = 0;
    uint64_t new_min = NO_BUCKET;
    for (size_t i = 0; i < overflow.size(); ++i) {
      const auto [bk, v] = overflow[i];
      if (bk - b < C) {
        push(bk, v);  // fits the window now -> goes to the ring
      } else {
        overflow[keep++] = {bk, v};
        new_min = std::min(new_min, bk);
      }
    }
    overflow.resize(keep);
    ovf_min = new_min;
  }

  std::vector<vid_t>& slot(uint64_t bucket) { return ring[bucket % C]; }

  // Call before detaching the contents of bucket's slot (the caller empties
  // the slot right after).
  void taken(uint64_t bucket) {
    const uint64_t s = bucket % C;
    in_ring -= ring[s].size();
    occ[s >> 6] &= ~(uint64_t{1} << (s & 63));
  }
};
