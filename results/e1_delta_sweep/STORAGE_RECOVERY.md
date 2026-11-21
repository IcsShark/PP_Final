# Streaming phase-log storage recovery

The E1/E2 workers now drain phase output through bounded FIFOs directly into the
existing Python reducers on the compute node. New jobs persist only reduced JSON,
never raw phase CSVs or gzip files. Both legacy gzip-derived summaries and the
new streaming summaries retain identical analysis inputs. Reducer errors stop
the producer and queue; summary totals and coverage must match verified CSVs.

## Checks

Local targeted suite (`PYTHONPATH=scripts/exp:analysis python3 -m unittest
scripts/exp/phase_stream_test.py scripts/exp/e1_test.py scripts/exp/e2_test.py
analysis/test_phase_reduce.py analysis/test_e1_analysis.py
analysis/test_e2_analysis.py -v`):

```text
Ran 30 tests in 1.021s
OK (skipped=1)
```

The skipped test needs the cluster's existing NY raw log. It was then executed
on compute with `run -c 12`, setting `NY_PHASE_LOG` to
`~/devin/results_raw/e1/stats_NY_delta-seq_all_pop_t1_b00_s0_source36023.phases.csv.gz`:

```text
Ran 1 test in 8.806s
OK
EXACT NY EQUIVALENCE e1_phase_reduce: 19 runs, 802522 phases in 1.493s; stats_NY_delta-seq_all_pop_t1_b00_s0_source36023.phases.csv.gz
EXACT NY EQUIVALENCE e2_phase_reduce: 19 runs, 802522 phases in 2.871s; stats_NY_delta-seq_all_pop_t1_b00_s0_source36023.phases.csv.gz
```

This compares every field of the old gzip reduction with the FIFO transport's
output, including empty-phase counters and both ideal-cost models. Synthetic
tests also cover headers/headerless output, empty and malformed output, producer
failure before FIFO open, and terminating a producer when reduction fails.

## Retry and queue

The approved failed grid raw `.phases.csv.partial`, its `.failed` marker, and
E1 `STOPPED` were removed. No other raw logs were deleted. The existing serial
driver restarted as PID 1310575 at 2026-11-19 18:48:31 +08:00, with an empty
scheduler. Every experiment still uses `run -c 12 -- timeout 1190`.

| Grid2896 job | Verified rows | Reduced phases | Worker seconds | Wrapper wall seconds | Summary bytes |
|---|---:|---:|---:|---:|---:|
| `stats_grid2896_delta-seq_all_pop_t1_b00_s0` | 48 | 241110832 | 497.16 | 498.0 | 19858 |
| `stats_grid2896_delta-seq_all_pop_t1_b01_s0` | 32 | 1246684 | 28.56 | 30.4 | 13008 |

The first job includes delta=1 and all four fixed sources. Both jobs finished
below 1190 seconds; no split or measurement omission was needed. All phases,
edges, heavy-pass totals, and run coverage matched the verified stats rows.
Both completion records have `phase_logs=[]` and hashed reduced summaries.

The 18:58 +08:00 snapshot had E1 99/760 jobs complete and NY/LJ E2 24/24 each.
The next grid OMP-t6 stats job was running, with no STOPPED flag.

The 208 existing NY/LJ gzip files across E1/E2 retained identical paths, sizes,
and nanosecond mtimes. The sorted metadata inventory SHA-256 before and after was
`0a10b81f32e72889bcb528eecd0a12a0a3248c7ed3caca5b54071edee297116c`.
No nonempty new raw phase files appeared after the restart. This is a metadata
preservation check, not a new full-content checksum scan of the old gzip files.

After deletion, NFS briefly continued returning `OSError: [Errno 122] Disk quota
exceeded` for a small inventory write. Writes and deployment then succeeded;
the driver was not restarted until deployment and the compute regression passed.
