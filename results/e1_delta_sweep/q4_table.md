# Q4: choosing Δ

Times: mean of four source-wise medians of three timing-build repetitions (ms).
The globally fastest variant/filter is held fixed for rule comparisons within each execution mode.
Overhead uses source-matched Dijkstra edges, averaged over four sources; it selects the last passing power-of-two sweep Δ.
The t12 overhead rule uses t6 stats as a proxy; t12 work counters were not measured.

| Graph | Mode | Variant/filter | Rule | Δ | Time (ms) | Slowdown |
|---|---|---|---|---:|---:|---:|
| NY | seq | all/pop | fastest | 256 | 12.083 | 1.000× |
| NY | seq | all/pop | W/d_max | 4618 | 12.371 | 1.024× |
| NY | seq | all/pop | W/d_avg | 13377 | 13.863 | 1.147× |
| NY | seq | all/pop | overhead_alpha=0.1 | 1024 | 12.166 | 1.007× |
| NY | seq | all/pop | overhead_alpha=0.25 | 4096 | 12.371 | 1.024× |
| NY | seq | all/pop | overhead_alpha=0.5 | 16384 | 14.475 | 1.198× |
| NY | seq | all/pop | overhead_alpha=1 | 32768 | 17.844 | 1.477× |
| NY | seq | all/pop | overhead_alpha=2 | 65536 | 25.637 | 2.122× |
| NY | t6 | all/pop | fastest | 16384 | 7.601 | 1.000× |
| NY | t6 | all/pop | W/d_max | 4618 | 8.366 | 1.101× |
| NY | t6 | all/pop | W/d_avg | 13377 | 7.621 | 1.003× |
| NY | t6 | all/pop | overhead_alpha=0.1 | 512 | 13.679 | 1.800× |
| NY | t6 | all/pop | overhead_alpha=0.25 | 4096 | 8.505 | 1.119× |
| NY | t6 | all/pop | overhead_alpha=0.5 | 16384 | 7.601 | 1.000× |
| NY | t6 | all/pop | overhead_alpha=1 | 32768 | 7.987 | 1.051× |
| NY | t6 | all/pop | overhead_alpha=2 | 65536 | 9.457 | 1.244× |
| NY | t12 | all/pop | fastest | 16384 | 8.330 | 1.000× |
| NY | t12 | all/pop | W/d_max | 4618 | 9.973 | 1.197× |
| NY | t12 | all/pop | W/d_avg | 13377 | 8.513 | 1.022× |
| NY | t12 | all/pop | overhead_alpha=0.1 | 512 | 18.192 | 2.184× |
| NY | t12 | all/pop | overhead_alpha=0.25 | 4096 | 10.288 | 1.235× |
| NY | t12 | all/pop | overhead_alpha=0.5 | 16384 | 8.330 | 1.000× |
| NY | t12 | all/pop | overhead_alpha=1 | 32768 | 8.383 | 1.006× |
| NY | t12 | all/pop | overhead_alpha=2 | 65536 | 9.112 | 1.094× |
| LJ | seq | all/pop | fastest | 1024 | 1201.243 | 1.000× |
| LJ | seq | all/pop | W/d_max | 13 | 1299.480 | 1.082× |
| LJ | seq | all/pop | W/d_avg | 18558 | 1718.903 | 1.431× |
| LJ | seq | all/pop | overhead_alpha=0.1 | 2048 | 1209.769 | 1.007× |
| LJ | seq | all/pop | overhead_alpha=0.25 | 8192 | 1269.125 | 1.057× |
| LJ | seq | all/pop | overhead_alpha=0.5 | 16384 | 1392.083 | 1.159× |
| LJ | seq | all/pop | overhead_alpha=1 | 16384 | 1392.083 | 1.159× |
| LJ | seq | all/pop | overhead_alpha=2 | 65536 | 2630.499 | 2.190× |
| LJ | t6 | all/merge | fastest | 4096 | 288.852 | 1.000× |
| LJ | t6 | all/merge | W/d_max | 13 | 599.220 | 2.074× |
| LJ | t6 | all/merge | W/d_avg | 18558 | 333.346 | 1.154× |
| LJ | t6 | all/merge | overhead_alpha=0.1 | 2048 | 289.279 | 1.001× |
| LJ | t6 | all/merge | overhead_alpha=0.25 | 8192 | 300.391 | 1.040× |
| LJ | t6 | all/merge | overhead_alpha=0.5 | 16384 | 324.785 | 1.124× |
| LJ | t6 | all/merge | overhead_alpha=1 | 16384 | 324.785 | 1.124× |
| LJ | t6 | all/merge | overhead_alpha=2 | 65536 | 517.433 | 1.791× |
| LJ | t12 | all/merge | fastest | 4096 | 254.635 | 1.000× |
| LJ | t12 | all/merge | W/d_max | 13 | 814.598 | 3.199× |
| LJ | t12 | all/merge | W/d_avg | 18558 | 289.204 | 1.136× |
| LJ | t12 | all/merge | overhead_alpha=0.1 | 2048 | 256.387 | 1.007× |
| LJ | t12 | all/merge | overhead_alpha=0.25 | 8192 | 261.953 | 1.029× |
| LJ | t12 | all/merge | overhead_alpha=0.5 | 16384 | 283.166 | 1.112× |
| LJ | t12 | all/merge | overhead_alpha=1 | 16384 | 283.166 | 1.112× |
| LJ | t12 | all/merge | overhead_alpha=2 | 65536 | 440.479 | 1.730× |
