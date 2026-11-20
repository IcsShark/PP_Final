# USA completion checks

## E1

2026-11-20 15:07 +08:00: USA E1 is 162/162 complete; USA E2 has automatically
started and is 18/24 complete. Driver PID 1310575 remains alive, with one
scheduler job and no STOPPED flag. E1 overall is 458/760 complete.

`python3 scripts/exp/e1_audit.py --graphs USA`:

```text
USA: 3888 verified rows; 0 gzip phase headers/first rows checked; 704 streamed phase runs checked
USA: jobs=162 compute_minutes=492.31 max_job_minutes=10.17 estimated_minutes=1304.46
BEST USA delta-seq t=1 all/pop delta=4096 mean_source_median_ms=1341.8748
BEST USA delta-omp t=6 all/pop delta=32768 mean_source_median_ms=531.5331
BEST USA delta-omp t=12 all/pop delta=32768 mean_source_median_ms=507.7597
```

All eight stats sweep curves have zero adjacent increases in mean phases. CSV
and summary hashes, nonzero work counters and phase/edge/heavy-pass totals agree.
Independent exact Cartesian-product coverage check:

```text
PASS: USA E1 162 jobs; exact source/delta/repetition coverage; {'dijkstra_stats': 4, 'dijkstra_timing': 12, 'timing': 3168, 'stats': 704} max_worker_seconds 610.48
```

`python3 analysis/e1_analysis.py`:

```text
PASS: analyzed complete graphs ['NY', 'LJ', 'grid2896', 'CTR', 'USA']; pending ['kron23', 'urand23', 'OK']
PASS: 120 Q4 rows, 30 Pop/Merge optimum comparisons, 80 empty-phase reduction comparisons
Phase reductions available: 3296/3296 stats runs
PASS: all prior four-graph E1 analysis CSV values exactly unchanged
```

Empty-expanded phases explain 4.57% of the all/Pop phase reduction from delta=1
to 524288 and 2.34% for light/heavy Pop; Merge has zero empty-expanded phases.
The USA timing PNG was visually checked. No job needed a retry or further split.
Remaining E1 estimate: 15.58 compute-hours, plus E2 and scheduler/NFS overhead.

## E2

2026-11-20 15:33 +08:00: all 24 USA E2 jobs are complete. Driver PID 1310575 has
continued to kron23, with one scheduler job and no STOPPED flag. E1 is 466/760.
The fixed pair is all/pop; both E1 anchors are 32768, with E2 candidates
{16384,32768,65536}.

```text
PASS: USA E2 24 jobs; exact source/delta/repetition coverage; {'timing': 216, 'stats': 72, 'reduced_phase_runs': 72} max_worker_seconds 48.21
PASS: 208 legacy NY/LJ gzip paths/sizes/mtimes unchanged; no new nonempty raw files since FIFO restart
PASS: 90 E2 Δ/thread points; 30 scaling rows; pending ['kron23', 'urand23', 'OK']
PASS: all prior four-graph E2 analysis CSV values exactly unchanged
```

E2 CSV, plan and phase-summary hashes pass. All 72 reduced runs match stats
phase/edge counters; ideal T1 equals scanned edges; max-term costs are at least
no-max costs at every thread count. The new USA Q3 PNG was visually checked.

| t | Best delta | ms | Speedup vs best E1 seq | Efficiency | Ideal max | Ideal no-max |
|---|---:|---:|---:|---:|---:|---:|
| 6 | 16384 | 517.520 | 2.593 | 43.2% | 5.979 | 5.986 |
| 12 | 32768 | 497.617 | 2.697 | 22.5% | 11.926 | 11.953 |

E2's t6 winner differs from E1's t6 anchor, within the measured candidate set.
Remaining E1 estimate is 15.30 compute-hours, plus remaining E2 and scheduler/NFS
overhead. kron23, urand23, OK, optional perf and final `results/SUMMARY.md` remain
pending.
