# E5 hardware counters

Counter estimates use (median(B) − median(A)) / 20, independently per event, from three A and three B process measurements. B has 24 SSSP calls; A has four. Kernel time is the median across three B invocations of the mean of four source-wise medians. Speedup uses the same graph/Δ t1.

## Measurements

| Graph | t | Time ms | Speedup | CPI | Misses/edge | Miss rate | BW GB/s | Triad GB/s | Memory stall | E2 deviation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LJ | 1 | 1197.636 | 1.000× | 3.247 | 1.883 | 64.0% | 7.603 | 15.5 | 53.9% | +2.40% |

## Conclusions from these measurements

- **LJ** (partial): CPI 3.247 at t=1 → 3.247 at t=1; estimated bandwidth 7.603 → 7.603 GB/s. The estimate reaches/exceeds the same-thread triad reference at none of the measured thread counts.
- USA: not measured yet (optional for OK and urand23).
- OK: not measured yet (optional for OK and urand23).
- urand23: not measured yet (optional for OK and urand23).

### Interpretation limits

- High CPI, saturation and memory-stall events are consistent with memory pressure, but do not by themselves prove a bandwidth bottleneck. CPI also includes spinning and instructions outside the timed SSSP kernel. A low bandwidth estimate with high CPI is consistent with latency limits, but cannot establish latency rather than synchronization or insufficient memory-level parallelism. This applies to optional urand23 too.
- These process-wide counters do not measure barrier time. Thus E5 alone cannot establish "road graph sync-bound". The existing E2 work/phase fit is descriptive, not a direct synchronization measurement.
- LLC-load-misses is unavailable. The required generic cache-misses counter is an LLC proxy, not a validated count of demand DRAM reads. Estimated DRAM BW: **lower bound, no prefetch/write-back**, as prescribed by the spec; this is a traffic-accounting assumption, not a strict bound on physical DRAM traffic. Cache line transfers can include cache/coherence effects. Retired L3-miss and offcore counts are also retained in the CSV; offcore requests are not all DRAM reads.
- Perf scales multiplexed events independently; subtraction amplifies sampling and run-to-run error. Counts include repeated per-source/SSSP housekeeping outside the kernel timer (e.g. reached-vertex scans), not only edge relaxation. The load subtraction removes fixed process costs statistically, not exactly.
- A separate timing-build verification run per graph is outside the perf measurements; this avoids charging Dijkstra and verification scans to the counters. The measured CSV verified=-1 means verification was not requested, not a failure. Verification CSV rows must all be verified=1.
- Edges scanned and E2 timings come from the exact same graph/Δ/thread setting in results/e2_scaling/all_runs.csv. Thread-dependent work can vary. All runs use seed 42, four sources, the frozen E2 variant/filter and dynamic,64 schedule.
- Triad GB/s references: t1=15.5, t2=18.3, t4=20.3, t6=19.7, t8=18.9, t12=18.5; DRAM random-access latency reference ≈67 ns. Neither was remeasured.
- Guest reports Intel i5-10500/KVM, 12 cores × 1 thread, 16 MiB L3. Whole-node run -c 12 is used even for t1. The guest topology is not evidence of SMT placement.
- Prior teammate-reported LJ CSR corruption remains a caveat; verification is against Dijkstra on the same read-only input, not an independent clean graph.

## Anomalies and completeness

- Completed 1/12 required and 0/12 optional combinations; 0 timings differ from same-Δ E2 by at least 10%.
- Minimum event running percentage: 49.00%. All eight events must be finite, positive and present in all six samples.
