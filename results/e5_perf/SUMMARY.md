# E5 hardware counters

Counter estimates use (median(B) − median(A)) / 20, independently per event, from three A and three B process measurements. B has 24 SSSP calls; A has four. Kernel time is the median across three B invocations of the mean of four source-wise medians. Speedup uses the same graph/Δ t1.

## Measurements

| Graph | t | Time ms | Speedup | CPI | Misses/edge | Miss rate | BW GB/s | Triad GB/s | Memory stall | E2 deviation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LJ | 1 | 1197.636 | 1.000× | 3.247 | 1.883 | 64.0% | 7.603 | 15.5 | 53.9% | +2.40% |
| LJ | 2 | 680.709 | 1.759× | 3.616 | 1.875 | 54.5% | 13.311 | 18.3 | 54.0% | -18.76% |
| LJ | 4 | 383.245 | 3.125× | 3.917 | 1.743 | 53.3% | 21.975 | 20.3 | 56.6% | -14.79% |
| LJ | 6 | 290.665 | 4.120× | 4.221 | 1.604 | 54.4% | 26.660 | 19.7 | 59.2% | -0.37% |
| LJ | 8 | 278.702 | 4.297× | 5.216 | 1.535 | 51.0% | 26.601 | 18.9 | 62.4% | +2.23% |
| LJ | 12 | 258.343 | 4.636× | 6.619 | 1.465 | 51.0% | 27.394 | 18.5 | 67.4% | +1.44% |
| USA | 1 | 1547.906 | 1.000× | 2.003 | 0.386 | 7.8% | 1.277 | 15.5 | 25.0% | +2.04% |
| USA | 2 | 1123.552 | 1.378× | 2.751 | 0.413 | 5.0% | 1.852 | 18.3 | 30.9% | +24.93% |
| USA | 4 | 645.038 | 2.400× | 2.730 | 0.423 | 4.8% | 3.293 | 20.3 | 33.5% | -1.02% |
| USA | 6 | 510.394 | 3.033× | 2.798 | 0.416 | 4.8% | 4.096 | 19.7 | 35.8% | -1.66% |
| USA | 8 | 542.914 | 2.851× | 3.465 | 0.426 | 4.1% | 3.945 | 18.9 | 40.9% | +8.22% |
| USA | 12 | 542.133 | 2.855× | 4.102 | 0.425 | 4.0% | 3.932 | 18.5 | 46.4% | +8.95% |

## Conclusions from these measurements

- **LJ** (complete): CPI 3.247 at t=1 → 6.619 at t=12; estimated bandwidth 7.603 → 27.394 GB/s. The estimate reaches/exceeds the same-thread triad reference at 4, 6, 8, 12.
  t6→t12 speedup is only 1.125×; t12 efficiency versus same-Δ t1 is 38.6%. All measured CPI values exceed one: True. CPI increases monotonically: True.
  At t12 the generic estimate is 1.48× the triad reference. For comparison, retired demand-load L3 misses ×64/time would give 8.338 GB/s. The event semantics differ: neither directly measures all DRAM traffic, and the triad result is a reference rather than a universal hard ceiling for every access pattern.
  **Four-evidence answer:** efficiency saturation is quantified above; CPI is above one and its thread trend is reported explicitly; the LLC proxy is high per edge; the generic bandwidth estimate reaches/exceeds the triad reference at the thread counts listed above. These qualitative signatures support memory pressure, but do not establish that physical DRAM bandwidth is saturated: event semantics, multiplexing and untimed housekeeping limit the bandwidth inference.
- **USA** (complete): CPI 2.003 at t=1 → 4.102 at t=12; estimated bandwidth 1.277 → 3.932 GB/s. The estimate reaches/exceeds the same-thread triad reference at none of the measured thread counts.
  t6→t12 speedup is only 0.941×; t12 efficiency versus same-Δ t1 is 23.8%. All measured CPI values exceed one: True. CPI increases monotonically: False.
  At t12 the generic estimate is 0.21× the triad reference. For comparison, retired demand-load L3 misses ×64/time would give 0.631 GB/s. The event semantics differ: neither directly measures all DRAM traffic, and the triad result is a reference rather than a universal hard ceiling for every access pattern.
- OK: not measured yet (optional for OK and urand23).
- urand23: not measured yet (optional for OK and urand23).
- **Road/social comparison**: at the highest measured threads (LJ t12, USA t12), USA CPI 4.102 vs LJ 6.619; USA bandwidth 3.932 vs LJ 27.394 GB/s. Use these observed values, not an assumption that the road CPI must be lower.

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

- Completed 12/12 required and 0/12 optional combinations; 3 timings differ from same-Δ E2 by at least 10%.
  - LJ t2: -18.76% (680.709 vs 837.894 ms). Retained without retuning.
  - LJ t4: -14.79% (383.245 vs 449.741 ms). Retained without retuning.
  - USA t2: +24.93% (1123.552 vs 899.322 ms). Retained without retuning.
- Minimum event running percentage: 49.00%. All eight events must be finite, positive and present in all six samples.
