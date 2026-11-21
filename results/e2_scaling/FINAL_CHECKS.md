# Final E0–E2 checks

At the 2026-11-21 02:44 +08:00 cluster checkpoint the scheduler was empty, no
STOPPED flag was present, and driver PID 1310575 had exited normally after:

```text
E1 AND E2 COMPLETE
```

There are 760 completed E1 jobs and 192 completed E2 jobs. The longest recorded
successful worker was `stats_grid2896_delta-seq_lh_pop_t1_b00_s0`, 868.8334 seconds,
below the 1190-second outer cap. The final per-graph source/delta/repetition audits
and CSV/plan/summary digests passed. Reduced phase/edge/heavy-pass counts agree
with stats CSVs; E2 ideal T1 equals edges, and max-term costs are no smaller than
no-max costs. Earlier graphs' numerical analysis values remained unchanged.

## Final all-graph analysis

`PYTHONDONTWRITEBYTECODE=1 python3 analysis/e1_analysis.py`:

```text
PASS: analyzed complete graphs ['NY', 'LJ', 'grid2896', 'CTR', 'USA', 'kron23', 'urand23', 'OK']; pending []
PASS: 192 Q4 rows, 48 Pop/Merge optimum comparisons, 128 empty-phase reduction comparisons
Phase reductions available: 5216/5216 stats runs
```

`PYTHONDONTWRITEBYTECODE=1 python3 analysis/e2_analysis.py`:

```text
PASS: 162 E2 Δ/thread points; 48 scaling rows; pending []
```

`PYTHONDONTWRITEBYTECODE=1 python3 analysis/summary.py`:

```text
PASS: SUMMARY.md generated for 8 graphs
```

## Focused tests on the VM

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts/exp:analysis python3 -m unittest \
  scripts/exp/phase_stream_test.py scripts/exp/e1_test.py scripts/exp/e2_test.py \
  analysis/test_phase_reduce.py analysis/test_e1_analysis.py \
  analysis/test_e2_analysis.py analysis/test_e2_hardware.py analysis/test_summary.py
```

```text
.s.....................................
----------------------------------------------------------------------
Ran 39 tests in 1.039s

OK (skipped=1)
```

The single skip is the real-NY gzip regression: `NY_PHASE_LOG` is unset on the VM,
where cluster raw logs are intentionally absent. That test previously passed on
a compute node for both reducers, with exact equality over 19 runs / 802522 phases;
the original output is recorded in `../e1_delta_sweep/STORAGE_RECOVERY.md`.

## Preservation and inspection

```text
PASS: all 208 legacy NY/LJ gzip paths/sizes/nanosecond mtimes unchanged; no new nonempty raw phase files
PASS: no raw phase logs, gzip CSV logs or .partial files tracked
```

Inspected PNGs for the new urand23/OK time and ideal plots, kron23 ideals and the
final all-graph Q2 scaling plot; earlier representative plots were inspected when
their graphs completed. No claim is made that every PDF/PNG was individually viewed.

No additional cluster measurements were added for reviewer analysis. The earlier
optional perf allocation was not run under the latest existing-data/no-new-runs
constraint; counter availability was not newly tested. E3/E4 context and the LJ
input issue are attributed to the teammate in SUMMARY, not independently audited.
