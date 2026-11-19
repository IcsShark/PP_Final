# CTR E1/E2 completion

2026-11-20 06:40 +08:00: CTR E1 is 106/106 and E2 is 24/24 complete. The serial
driver remains PID 1310575 and has moved to USA. Snapshot: E1 301/760, one
scheduler job, no STOPPED flag; NY/LJ/grid/CTR E2 are all complete.

`python3 scripts/exp/e1_audit.py --graphs CTR` reported:

```text
CTR: 3712 verified rows; 0 gzip phase headers/first rows checked; 672 streamed phase runs checked
CTR: jobs=106 compute_minutes=279.04 max_job_minutes=7.87 estimated_minutes=775.24
BEST CTR delta-seq t=1 all/pop delta=4096 mean_source_median_ms=909.1649
BEST CTR delta-omp t=6 all/pop delta=16384 mean_source_median_ms=324.0900
BEST CTR delta-omp t=12 all/pop delta=32768 mean_source_median_ms=317.4086
```

All eight stats sweep curves had zero adjacent mean-phase increases. CSV and
summary digests, nonzero counters, and phase/edge/heavy-pass totals agree.
An independent source/delta/repetition Cartesian-product audit reported:

```text
PASS: e1_delta_sweep CTR 106 jobs; exact source/delta/repetition coverage; {'dijkstra_stats': 4, 'dijkstra_timing': 12, 'timing': 3024, 'stats': 672} max_worker_seconds 472.31
PASS: e2_scaling CTR 24 jobs; exact source/delta/repetition coverage; {'timing': 288, 'stats': 96, 'reduced_phase_runs': 96} max_worker_seconds 36.59
```

All E2 plan/summary hashes and counter matches passed. Each ideal T1 equals total
scanned edges; max-term costs are at least no-max costs at every thread count.
The 208 existing NY/LJ gzip path/size/mtime records remain unchanged; no new
nonempty raw files exist since the FIFO restart. No job reached the cap.

The rerun analyses reported:

```text
PASS: analyzed complete graphs ['NY', 'LJ', 'grid2896', 'CTR']; pending ['USA', 'kron23', 'urand23', 'OK']
PASS: 96 Q4 rows, 24 Pop/Merge optimum comparisons, 64 empty-phase reduction comparisons
Phase reductions available: 2592/2592 stats runs
PASS: prior NY/LJ/grid results exactly unchanged in e1_delta_sweep analysis CSVs
PASS: 72 E2 Δ/thread points; 24 scaling rows; pending ['USA', 'kron23', 'urand23', 'OK']
PASS: prior NY/LJ/grid results exactly unchanged in e2_scaling analysis CSVs
```

E2 holds all/pop fixed at delta={8192,16384,32768,65536}. Its best t6 point is
327.972 ms, 2.772x versus best E1 sequential, with ideals 5.979x/5.986x. At t12 it
is 308.610 ms, 2.946x, with ideals 11.928x/11.955x. The empty-expanded attribution
from delta=1 to 262144 is 4.55% for all/Pop and 2.32% for light/heavy Pop; Merge
has zero empty-expanded phases. The new CTR timing and Q3 PNGs were visually
checked. Full Q1/Q4 and E2 tables now cover four graphs.

Remaining E1 estimate: 23.47 compute-hours, plus E2 and scheduler/NFS overhead.
USA, kron23, urand23, OK, optional perf and final `results/SUMMARY.md` are pending.
