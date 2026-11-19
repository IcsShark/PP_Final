# Q1: work, depth and empty phases

Primary definition: a logged phase is empty when `expanded == 0`. `frontier == 0` and `edges == 0` are separate diagnostics in `q1_metrics.csv`.
Counts below are arithmetic means across the four fixed sources. The attribution compares the smallest to the largest power-of-two sweep Δ.

| Graph | Mode | Variant/filter | Δ endpoints | Phases, small → large | Empty expanded, small → large | Empty share of phase reduction |
|---|---|---|---|---:|---:|---:|
| NY | seq | all/pop | 1 → 65536 | 245998.50 → 1213.00 | 23429.50 → 0.00 | 9.57% |
| NY | seq | all/merge | 1 → 65536 | 222569.00 → 1213.00 | 0.00 → 0.00 | 0.00% |
| NY | seq | lh/pop | 1 → 65536 | 468567.50 → 1230.00 | 23429.50 → 0.00 | 5.01% |
| NY | seq | lh/merge | 1 → 65536 | 445138.00 → 1230.00 | 0.00 → 0.00 | 0.00% |
| NY | t6 | all/pop | 1 → 65536 | 245999.00 → 1214.75 | 23430.00 → 0.00 | 9.57% |
| NY | t6 | all/merge | 1 → 65536 | 222569.00 → 1212.75 | 0.00 → 0.00 | 0.00% |
| NY | t6 | lh/pop | 1 → 65536 | 468566.00 → 1231.25 | 23428.00 → 0.00 | 5.01% |
| NY | t6 | lh/merge | 1 → 65536 | 445138.00 → 1233.25 | 0.00 → 0.00 | 0.00% |
| LJ | seq | all/pop | 1 → 262144 | 429808.00 → 62.50 | 17699.25 → 0.00 | 4.12% |
| LJ | seq | all/merge | 1 → 262144 | 412108.75 → 62.50 | 0.00 → 0.00 | 0.00% |
| LJ | seq | lh/pop | 1 → 262144 | 841916.75 → 68.00 | 17699.25 → 0.00 | 2.10% |
| LJ | seq | lh/merge | 1 → 262144 | 824217.50 → 68.00 | 0.00 → 0.00 | 0.00% |
| LJ | t6 | all/pop | 1 → 262144 | 429807.75 → 65.00 | 17699.00 → 0.00 | 4.12% |
| LJ | t6 | all/merge | 1 → 262144 | 412108.75 → 63.75 | 0.00 → 0.00 | 0.00% |
| LJ | t6 | lh/pop | 1 → 262144 | 841916.50 → 70.75 | 17699.00 → 0.00 | 2.10% |
| LJ | t6 | lh/merge | 1 → 262144 | 824217.50 → 71.50 | 0.00 → 0.00 | 0.00% |
| grid2896 | seq | all/pop | 1 → 262144 | 10822252.75 → 9717.25 | 2609731.25 → 0.00 | 24.14% |
| grid2896 | seq | all/merge | 1 → 262144 | 8212521.50 → 9717.25 | 0.00 → 0.00 | 0.00% |
| grid2896 | seq | lh/pop | 1 → 262144 | 19034774.25 → 10715.50 | 2609731.25 → 0.00 | 13.72% |
| grid2896 | seq | lh/merge | 1 → 262144 | 16425043.00 → 10715.50 | 0.00 → 0.00 | 0.00% |
| grid2896 | t6 | all/pop | 1 → 262144 | 10822252.75 → 9709.00 | 2609731.25 → 0.00 | 24.14% |
| grid2896 | t6 | all/merge | 1 → 262144 | 8212521.50 → 9709.00 | 0.00 → 0.00 | 0.00% |
| grid2896 | t6 | lh/pop | 1 → 262144 | 19034775.00 → 10704.00 | 2609732.00 → 0.00 | 13.72% |
| grid2896 | t6 | lh/merge | 1 → 262144 | 16425043.00 → 10708.75 | 0.00 → 0.00 | 0.00% |

The residual phase reduction comes from fewer nonempty phases, not fewer empty phases. See `q1_phase_reduction.csv` for comparisons against each pair’s best Δ as well.

## Does Merge move the fastest Δ?

| Graph | Mode | Variant | Pop best Δ / ms | Merge best Δ / ms | Δ changed? |
|---|---|---|---:|---:|---|
| NY | seq | all | 256 / 12.083 | 1024 / 13.733 | yes |
| NY | seq | lh | 4618 / 15.549 | 4618 / 17.052 | no |
| NY | t6 | all | 16384 / 7.601 | 16384 / 8.016 | no |
| NY | t6 | lh | 16384 / 11.587 | 13377 / 12.111 | yes |
| NY | t12 | all | 16384 / 8.330 | 32768 / 8.778 | yes |
| NY | t12 | lh | 32768 / 11.093 | 32768 / 12.124 | no |
| LJ | seq | all | 1024 / 1201.243 | 1024 / 1216.179 | no |
| LJ | seq | lh | 32 / 1472.572 | 128 / 1449.612 | yes |
| LJ | t6 | all | 2048 / 324.661 | 4096 / 288.852 | yes |
| LJ | t6 | lh | 2048 / 391.162 | 2048 / 388.459 | no |
| LJ | t12 | all | 4096 / 258.152 | 4096 / 254.635 | no |
| LJ | t12 | lh | 8192 / 346.125 | 4096 / 341.827 | yes |
| grid2896 | seq | all | 65536 / 561.634 | 32768 / 610.513 | yes |
| grid2896 | seq | lh | 2048 / 667.402 | 2048 / 708.410 | no |
| grid2896 | t6 | all | 262144 / 178.526 | 262144 / 190.043 | no |
| grid2896 | t6 | lh | 131072 / 291.069 | 262144 / 298.309 | yes |
| grid2896 | t12 | all | 262144 / 150.330 | 262144 / 161.731 | no |
| grid2896 | t12 | lh | 262144 / 213.644 | 262144 / 232.602 | no |

## Coverage

Complete graphs: NY, LJ, grid2896. Pending: CTR, USA, kron23, urand23, OK.
Reduced phase runs matched to stats CSVs: 1920 / 1920.
Work/depth plots use seq/t6 stats; timing plots also include measured t12 timings. Each performance point is the mean of four per-source medians of three repetitions.
