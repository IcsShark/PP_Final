# E2 NY/LJ snapshot

Both complete grids use the same four sources as E1 and reuse E1's best sequential
and normal-build Dijkstra baseline timings. All 576 CSV rows are verified: 432
timing repetitions and 144 stats runs. All 144 stats runs have matching small
phase-cost summaries; raw gzip logs remain on the cluster.

Selection: NY all/pop at Δ=8192,16384,32768; LJ all/merge at Δ=2048,4096,8192.
Each anchor's adjacent power-of-two sweep points are included. Q2/table rows pick
the fastest candidate Δ at each thread count; Q3 panels hold Δ fixed.

## Observations

- NY peaks at t6: 7.846 ms, 1.540× best E1 delta-seq. At t12 it takes 8.912 ms,
  1.356× seq: about 13.6% slower than t6. LJ improves from 291.744 ms at t6 to
  254.667 ms at t12 (12.7% less time), reaching 4.717× seq and 15.366× Dijkstra.
- At t12's winning Δ, NY averages 1,528 phases and 705 edges/phase; LJ averages
  594.75 phases and 126,951 edges/phase. LJ scales better in these two graphs,
  consistent with more work per phase and better amortization of synchronization.
  Remaining graph types are needed before drawing a general topology conclusion.
- At t12 the vertex-bound / no-bound ideals are NY 11.826× / 11.904× and LJ
  11.957× / 11.999×. The vertex maximum is not the main limitation in this tested
  Δ range. Measured OMP-t1 speedups at those same Δ values are only NY 1.745× and
  LJ 4.593×. The edge-work model therefore leaves substantial headroom, but does
  not distinguish memory costs, synchronization, scheduling, and other omitted
  costs. No perf counters were collected; memory latency is not established as
  the cause. The guest topology observed in E0 was 12 cores × 1 thread, so a
  six-physical-core interpretation is not assumed.
- Table efficiency is seq speedup / threads; it is not the same as efficiency
  relative to OMP t1. LJ's t1 efficiency exceeds 100% because its measured OMP
  configuration is slightly faster than the separately measured E1 sequential
  baseline. `all_runs.csv` also provides same-Δ OMP-t1 efficiency.

## Queue snapshot and ETA

NY: 24 jobs, 11.76 minutes summed wrapper wall time, 0.91 worker minutes.
LJ: 24 jobs, 13.22 minutes summed wrapper wall time, 9.92 worker minutes.
Whole-node allocation is used even at one thread; startup/scheduler/NFS overhead
dominates NY's short jobs but is excluded from CSV kernel times.

After these E2 runs, the combined driver resumed E1 on grid2896. At the snapshot,
92/760 E1 jobs were complete. The observed/model extrapolation gives 18.56 hours
of remaining E1 compute (ratio 0.2098). Allow a further 2–4 hours for E2 on the
six remaining graphs, plus scheduling/NFS and modeling uncertainty: budget
approximately **22–28 hours remaining**. The E2 allowance is a planning estimate,
not a measurement of the larger graphs. Recheck with `scripts/exp/e2_status.py`.
