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
