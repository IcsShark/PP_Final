#pragma once
#include <cstdint>
#include <limits>

using vid_t = uint32_t;     // vertex id (graphs up to 2^32 - 1 vertices)
using eid_t = uint64_t;     // edge index into CSR arrays
using weight_t = uint32_t;  // edge weight (non-negative integer)
using dist_t = uint64_t;    // tentative distance (64-bit so path sums never overflow)

inline constexpr dist_t INF = std::numeric_limits<dist_t>::max();
inline constexpr uint64_t NO_BUCKET = std::numeric_limits<uint64_t>::max();

#ifdef SSSP_STATS
inline constexpr bool kStatsEnabled = true;
#else
inline constexpr bool kStatsEnabled = false;
#endif
