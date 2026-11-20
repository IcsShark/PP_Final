# OK completion

All 98 OK E1 jobs completed by the 2026-11-21 02:23 +08:00 checkpoint, bringing
the complete E1 grid to 760/760. The live shared driver automatically started E2.

```text
OK: 3536 verified rows; 0 gzip phase headers/first rows checked; 640 streamed phase runs checked
OK: jobs=98 compute_minutes=197.76 max_job_minutes=4.34 estimated_minutes=823.31
PASS: OK E1 98 jobs; exact source/delta/repetition coverage (Dijkstra records delta=0)
```

All eight mean phase sweeps have zero adjacent increases. Summary digests and
phase/edge/heavy-pass counters agree with the verified stats CSVs. No raw phase
logs were written; every new stats completion names its streamed summary.

| Mode | Variant/filter | Fastest Δ | Mean source-median ms |
|---|---|---:|---:|
| seq | all/merge | 512 | 2690.5898 |
| t6 | all/merge | 1024 | 607.3513 |
| t12 | all/merge | 1024 | 562.2912 |

All-graph E1 analysis reports 192 Q4 rows, 48 Pop/Merge optimum comparisons,
128 phase-reduction comparisons and 5216/5216 reduced stats runs. Previous seven
graphs' Q4 values are unchanged. The OK time PNG was inspected. At this checkpoint
E2 had completed 6/24 OK jobs; no STOPPED flag or second scheduler job was present.

## E2 and queue exit

All 24 OK E2 jobs completed by 02:33:52 +08:00. The fixed pair is all/merge and
the candidates are {512,1024,2048}. Independent validation reported:

```text
PASS: OK E2 24 jobs; exact source/delta/repetition coverage; {'timing': 216, 'stats': 72, 'reduced_phase_runs': 72}
PASS: E1/plan/CSV/summary digests; CSV/phase counters; ideal T1=edges and max>=no-max costs; previous seven graphs unchanged
```

| t | Fastest candidate Δ | ms | vs best E1 seq | Efficiency | Ideal max / no-max |
|---|---:|---:|---:|---:|---:|
| 6 | 1024 | 604.577 | 4.450× | 74.2% | 5.994× / 6.000× |
| 12 | 1024 | 559.827 | 4.806× | 40.1% | 11.962× / 12.000× |

E2 used 15.25 compute-minutes / 16.15 wrapper-minutes. The all-graph analysis
covers 162 Δ/thread points and 48 scaling rows with no pending graph. Updated
Q3 models include all eight graphs. The final Q2 scaling and OK ideal PNGs were
inspected. The shared driver exited normally with `E1 AND E2 COMPLETE`, after
760/760 E1 and 192/192 E2 jobs. The 02:44 checkpoint found an empty scheduler
and no STOPPED flags. Final raw inventory checks preserved all 208 legacy files
and found no new nonempty raw phase files.
