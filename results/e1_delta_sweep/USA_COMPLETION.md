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

USA E2 final checks and perf remain pending at this snapshot; no final
`results/SUMMARY.md` has been written yet.
