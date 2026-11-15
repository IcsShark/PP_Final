#pragma once
#include <atomic>

#include "types.hpp"

// Relaxed atomic load of a plain dist_t slot (avoids a formal data race when
// another thread may be lowering the same slot).
inline dist_t atomic_load_relaxed(dist_t& slot) {
  return std::atomic_ref<dist_t>(slot).load(std::memory_order_relaxed);
}

// atomicMin: lowers slot to val if val is strictly smaller.
// Returns true iff this call performed the update.
inline bool atomic_min(dist_t& slot, dist_t val) {
  std::atomic_ref<dist_t> ref(slot);
  dist_t old = ref.load(std::memory_order_relaxed);
  while (val < old) {
    if (ref.compare_exchange_weak(old, val, std::memory_order_relaxed)) return true;
  }
  return false;
}
