# E2 thread scaling

Timing: mean of four source-wise medians of three normal-build repetitions. Each row chooses the fastest measured Δ at that thread count from the frozen E2 candidate set.
Efficiency below = speedup vs best E1 delta-seq / threads. CSVs also provide OMP-t1 efficiency.
Ideal speedups average source-matched T1/Tk on each row’s own measured phase decomposition; T1=sum(edges). The measured-vs-ideal figures use OMP-t1 at the SAME Δ as their measured baseline.
E0 guest topology was 12 cores × 1 thread; a six-physical-core knee is a hypothesis, not assumed hardware.

| Graph | t | Δ | ms | vs seq | vs Dijkstra | Efficiency | Ideal max | Ideal no-max | Phases | Edges/phase |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LJ | 1 | 2048 | 1162.492 | 1.033 | 3.366 | 103.3% | 1.000 | 1.000 | 912.5 | 78316.8 |
| LJ | 2 | 4096 | 837.894 | 1.434 | 4.670 | 71.7% | 2.000 | 2.000 | 595.2 | 126890.6 |
| LJ | 4 | 2048 | 446.609 | 2.690 | 8.762 | 67.2% | 3.997 | 4.000 | 912.2 | 78313.8 |
| LJ | 6 | 4096 | 291.744 | 4.117 | 13.413 | 68.6% | 5.994 | 6.000 | 595.2 | 126811.2 |
| LJ | 8 | 2048 | 271.788 | 4.420 | 14.398 | 55.2% | 7.978 | 8.000 | 912.2 | 78348.8 |
| LJ | 12 | 4096 | 254.667 | 4.717 | 15.366 | 39.3% | 11.957 | 11.999 | 594.8 | 126950.6 |
| NY | 1 | 8192 | 14.199 | 0.851 | 1.542 | 85.1% | 1.000 | 1.000 | 1793.5 | 529.7 |
| NY | 2 | 8192 | 12.510 | 0.966 | 1.751 | 48.3% | 1.998 | 1.998 | 1786.8 | 535.3 |
| NY | 4 | 16384 | 8.444 | 1.431 | 2.594 | 35.8% | 3.988 | 3.992 | 1525.5 | 705.3 |
| NY | 6 | 16384 | 7.846 | 1.540 | 2.791 | 25.7% | 5.967 | 5.978 | 1527.0 | 704.1 |
| NY | 8 | 16384 | 8.024 | 1.506 | 2.729 | 18.8% | 7.934 | 7.960 | 1530.0 | 702.7 |
| NY | 12 | 16384 | 8.912 | 1.356 | 2.457 | 11.3% | 11.826 | 11.904 | 1528.0 | 705.0 |
