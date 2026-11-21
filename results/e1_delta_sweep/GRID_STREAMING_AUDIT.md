# Grid2896: streaming E1 and E2 completion

Snapshot: 2026-11-20 01:36 +08:00. All 114 grid E1 jobs and all 12 grid E2 jobs
are complete. The serial driver (PID 1310575) has continued to CTR without a
restart, with one scheduler job and no STOPPED flag. E1 is 193/760 complete;
NY/LJ/grid E2 are 24/24, 24/24, and 12/12 complete respectively.

## Checks

`python3 scripts/exp/e1_audit.py --graphs grid2896`:

```text
grid2896: 3536 verified rows; 0 gzip phase headers/first rows checked; 640 streamed phase runs checked
grid2896: jobs=114 compute_minutes=451.34 max_job_minutes=14.48 estimated_minutes=873.70
BEST grid2896 delta-seq t=1 all/pop delta=65536 mean_source_median_ms=561.6339
BEST grid2896 delta-omp t=6 all/pop delta=262144 mean_source_median_ms=178.5260
BEST grid2896 delta-omp t=12 all/pop delta=262144 mean_source_median_ms=150.3298
```

All eight algorithm/variant/filter stats sweeps had zero adjacent increases in
mean phase count. CSVs and phase summaries match their completion-record hashes;
phase/edge/heavy-pass totals agree. An independent Cartesian-product check of
source, delta and repetition coverage reported:

```text
PASS: e1_delta_sweep grid2896 114 jobs; exact source/delta/repetition coverage; {'dijkstra_stats': 4, 'dijkstra_timing': 12, 'timing': 2880, 'stats': 640}
PASS: e2_scaling grid2896 12 jobs; exact source/delta/repetition coverage; {'timing': 144, 'stats': 48, 'reduced_phase_runs': 48}
```

E2 plan and summary hashes were also checked. All 48 E2 reduced phase runs match
their verified stats CSVs; both ideal-model T1 costs equal total scanned edges,
and the vertex-max cost is at least the no-max cost for every thread count.

The slowest grid stats worker was
`stats_grid2896_delta-seq_lh_pop_t1_b00_s0`, at **868.83 seconds**. The complete
grid therefore fits the 1190-second cap without further splitting or omissions,
including the previously projected large light/heavy block. The slowest timing
worker took 752.98 seconds. No new nonempty files appeared in either raw-log
directory after the FIFO-driver restart. All 208 legacy NY/LJ gzip paths, sizes
and nanosecond mtimes still match the saved pre-restart inventory (SHA-256
`0a10b81f32e72889bcb528eecd0a12a0a3248c7ed3caca5b54071edee297116c`).
This is a metadata preservation check, not a full gzip-content checksum scan.

## Regenerated analyses

`python3 analysis/e1_analysis.py` and `python3 analysis/e2_analysis.py`:

```text
PASS: analyzed complete graphs ['NY', 'LJ', 'grid2896']; pending ['CTR', 'USA', 'kron23', 'urand23', 'OK']
PASS: 72 Q4 rows, 18 Pop/Merge optimum comparisons, 48 empty-phase reduction comparisons
Phase reductions available: 1920/1920 stats runs
PASS: legacy NY/LJ values exactly unchanged in all four E1 analysis CSVs with mixed version-1/version-2 summaries
PASS: 48 E2 Δ/thread points; 18 scaling rows; pending ['CTR', 'USA', 'kron23', 'urand23', 'OK']
PASS: legacy NY/LJ values exactly unchanged in both E2 analysis CSVs with new streamed grid summaries
```

Grid E2 freezes all/pop at delta={131072,262144}: both E1 anchors are the sweep's
upper endpoint, so only its lower neighbour exists. At t6, the best point is
177.502 ms, 3.164x versus best E1 sequential, with ideals 5.995x/5.997x. At t12 it
is 152.224 ms, 3.690x, with ideals 11.973x/11.988x. Q3 retains same-delta OMP-t1
baselines for its measured-versus-ideal comparison.

For all/pop, empty-expanded phases account for 24.14% of the phase reduction
from delta=1 to 262144; for light/heavy Pop, 13.72%; Merge has zero empty-expanded
phases. Full Q1/Q4 tables and PDF/PNG plots now cover NY, LJ and grid2896.
The new grid time and Q3 PNGs were visually checked for labels, curves and layout.

Remaining E1 model estimate is 29.29 compute-hours, plus remaining E2 and
scheduler/NFS overhead. This supersedes the earlier optimistic ETA. Five graphs,
optional perf and the final all-graph `results/SUMMARY.md` are still pending.
