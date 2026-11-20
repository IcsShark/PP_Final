# urand23 completion

E1 completed on 2026-11-20 (+08:00). The shared driver remained alive as PID
1310575, automatically moving into urand23 E2 without a restart or second job.

`python3 scripts/exp/e1_audit.py --graphs urand23`:

```text
urand23: 3536 verified rows; 0 gzip phase headers/first rows checked; 640 streamed phase runs checked
urand23: jobs=114 compute_minutes=222.23 max_job_minutes=3.68 estimated_minutes=938.73
```

Independent Cartesian-product coverage passed for all 114 jobs, including the
four fixed sources and every requested repetition and Δ. Dijkstra records Δ=0
(its planner placeholder is 1); delta-stepping rows match the planned Δ values.
Every stats phase/edge/heavy-pass count agrees with its atomic streamed summary.
All eight algorithm/variant/filter phase sweeps have zero adjacent increases.

| Mode | Variant/filter | Fastest Δ | Mean source-median ms |
|---|---|---:|---:|
| seq | all/pop | 1024 | 3366.7350 |
| t6 | all/merge | 1024 | 929.7471 |
| t12 | all/merge | 4096 | 847.7322 |

E1 analysis now covers seven graphs, with 168 Q4 rows and 4576/4576 reduced
stats runs. Previous six-graph Q4 rows are unchanged. The time PNG was inspected.
All 208 legacy NY/LJ gzip paths, sizes and nanosecond mtimes remain unchanged;
no new nonempty raw phase files exist. E2 was still running at this checkpoint.
