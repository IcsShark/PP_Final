# E0–E2 experiment summary

All eight E1/E2 graph queues completed. E3/Q3a and E4 are teammate-owned and were not run or merged by this agent. Tables below are generated from committed analysis CSVs by `python3 analysis/summary.py`; detailed input hashes are in each experiment’s `ANALYSIS_META.json`.

## Measurement contract

- Times are means over four fixed sources, each source taking the median of three timing-build repetitions. Stats-build times are never used as performance numbers. All rows are verified against Dijkstra.
- All timing/stats allocations used whole-node `run -c 12`, including one-thread runs. E0 observed i5-10500/KVM guest topology **12 cores × 1 thread**, L3 **16 MiB**; six physical cores and a six-core SMT knee are not established by the guest report.
- E1 holds each mode’s fastest variant/filter fixed when comparing Δ-selection rules. E2 freezes the globally fastest E1 OpenMP pair and tests the t6/t12 anchors and their sweep neighbours. Consequently E2’s t6 pair need not equal E1’s independent t6 winner.
- New phase data were reduced through bounded FIFOs, never persisted as raw logs. The 208 legacy NY/LJ gzip paths/sizes/nanosecond mtimes were preserved. The quota failure and successful retry are documented in `e1_delta_sweep/STORAGE_RECOVERY.md`.

## Q1 — Δ trades depth for redundant work

All audited mean phase sweeps are nonincreasing. The timing minima generally occur between the work-heavy large-Δ and phase-heavy small-Δ extremes; **grid2896 OpenMP instead wins at the largest tested sweep Δ**, so its unconstrained optimum is not established. Merge can move an optimum (e.g. NY sequential 256→1024; LJ t6 all 2048→4096), but is not a universal speedup.

### Fastest E1 Δ / milliseconds (variant/filter)

| Graph | seq | t6 | t12 |
|---|---|---|---|
| NY | 256 / 12.083 (all/pop) | 16384 / 7.601 (all/pop) | 16384 / 8.330 (all/pop) |
| LJ | 1024 / 1201.243 (all/pop) | 4096 / 288.852 (all/merge) | 4096 / 254.635 (all/merge) |
| grid2896 | 65536 / 561.634 (all/pop) | 262144 / 178.526 (all/pop) | 262144 / 150.330 (all/pop) |
| CTR | 4096 / 909.165 (all/pop) | 16384 / 324.090 (all/pop) | 32768 / 317.409 (all/pop) |
| USA | 4096 / 1341.875 (all/pop) | 32768 / 531.533 (all/pop) | 32768 / 507.760 (all/pop) |
| kron23 | 64 / 1789.946 (all/pop) | 128 / 488.383 (all/merge) | 2048 / 487.066 (lh/pop) |
| urand23 | 1024 / 3366.735 (all/pop) | 1024 / 929.747 (all/merge) | 4096 / 847.732 (all/merge) |
| OK | 512 / 2690.590 (all/merge) | 1024 / 607.351 (all/merge) | 1024 / 562.291 (all/merge) |

### Empty phases

Primary definition: `expanded == 0`; `frontier == 0` is separate, not an expanded/frontier quotient. Initial shares below are ratios of mean empty to mean total phases across four sources at Δ=1, OpenMP t6. Attribution is `(empty_small−empty_large)/(phases_small−phases_large)` for all/pop, Δ=1→largest sweep Δ. Thus an initial empty fraction and a fraction of phase reduction are different quantities. Heavy passes are included. Zero logged empty frontiers does not imply zero filtering cost.

| Graph | all/pop | lh/pop | all/merge | lh/merge | Largest Δ | Empty attribution all/pop |
|---|---|---|---|---|---|---|
| NY | 9.52% | 5.00% | 0.00% | 0.00% | 65536 | 9.57% |
| LJ | 4.12% | 2.10% | 0.00% | 0.00% | 262144 | 4.12% |
| grid2896 | 24.11% | 13.71% | 0.00% | 0.00% | 262144 | 24.14% |
| CTR | 4.54% | 2.32% | 0.00% | 0.00% | 262144 | 4.55% |
| USA | 4.56% | 2.33% | 0.00% | 0.00% | 524288 | 4.57% |
| kron23 | 0.41% | 0.20% | 0.00% | 0.00% | 262144 | 0.41% |
| urand23 | 37.22% | 22.87% | 0.00% | 0.00% | 262144 | 37.23% |
| OK | 37.17% | 22.82% | 0.00% | 0.00% | 262144 | 37.17% |

Most phase reduction is from fewer **nonempty** phases, not empty phases. Full source-normalized work, expansions/reached and phases/buckets are in `e1_delta_sweep/q1_metrics.csv`; all per-pair comparisons are in `q1_phase_reduction.csv` and `q1_merge_best.csv` in the same directory.

## Q2 — topology and measured scaling

Social/random graphs have far more edges per phase than road graphs. NY peaks at t6 and slows at t12; LJ continues improving. This supports topology-dependent scaling, not a blanket claim that every social/synthetic graph scales identically. Each row below uses its fastest frozen E2 candidate Δ. Efficiency = speedup vs best E1 delta-seq / threads; the ideals use each row’s phase decomposition, while Q3 plots compare measured OMP-t1 at the **same Δ**.

| Graph | t | Δ | ms | vs seq | vs Dijkstra | Efficiency | Ideal max / no-max | Phases | Edges/phase |
|---|---|---|---|---|---|---|---|---|---|
| NY | 6 | 16384 | 7.846 | 1.540× | 2.791× | 25.7% | 5.967 / 5.978 | 1527.0 | 704.1 |
| NY | 12 | 16384 | 8.912 | 1.356× | 2.457× | 11.3% | 11.826 / 11.904 | 1528.0 | 705.0 |
| LJ | 6 | 4096 | 291.744 | 4.117× | 13.413× | 68.6% | 5.994 / 6.000 | 595.2 | 126811.2 |
| LJ | 12 | 4096 | 254.667 | 4.717× | 15.366× | 39.3% | 11.957 / 11.999 | 594.8 | 126950.6 |
| grid2896 | 6 | 262144 | 177.502 | 3.164× | 6.818× | 52.7% | 5.995 / 5.997 | 9702.5 | 4630.3 |
| grid2896 | 12 | 262144 | 152.224 | 3.690× | 7.950× | 30.7% | 11.973 / 11.988 | 9703.8 | 4631.3 |
| CTR | 6 | 16384 | 327.972 | 2.772× | 5.181× | 46.2% | 5.979 / 5.986 | 36593.8 | 1128.7 |
| CTR | 12 | 32768 | 308.610 | 2.946× | 5.506× | 24.6% | 11.928 / 11.955 | 30528.8 | 1509.9 |
| USA | 6 | 16384 | 517.520 | 2.593× | 5.126× | 43.2% | 5.979 / 5.986 | 65460.2 | 1080.0 |
| USA | 12 | 32768 | 497.617 | 2.697× | 5.331× | 22.5% | 11.926 / 11.953 | 54805.8 | 1444.2 |
| kron23 | 6 | 1024 | 521.226 | 3.434× | 7.006× | 57.2% | 6.000 / 6.000 | 1209.5 | 108693.0 |
| kron23 | 12 | 2048 | 486.874 | 3.676× | 7.501× | 30.6% | 11.994 / 12.000 | 673.8 | 196496.5 |
| urand23 | 6 | 1024 | 929.166 | 3.623× | 8.548× | 60.4% | 5.999 / 6.000 | 839.2 | 161215.2 |
| urand23 | 12 | 1024 | 848.043 | 3.970× | 9.366× | 33.1% | 11.996 / 12.000 | 839.2 | 161215.2 |
| OK | 6 | 1024 | 604.577 | 4.450× | 9.981× | 74.2% | 5.994 / 6.000 | 569.0 | 453136.6 |
| OK | 12 | 1024 | 559.827 | 4.806× | 10.779× | 40.1% | 11.962 / 12.000 | 569.0 | 452805.8 |

## Q3 — work-only headroom, phase costs and memory

Both work-only ideals are almost linear, far above measured speedups. The maximum-vertex term alone therefore does not explain the gap. A phase-aware model is fitted below from **existing data only**. Its phase/sync component is not a direct barrier-time measurement. In particular, kron23 has a large winning-t12 residual despite a seemingly good aggregate R²; do not interpret its fitted split as an accurate physical decomposition.

Teammate-provided E4 context reports road-graph phase counts roughly **40×** GAPBS iterations. This is consistent with substantial per-phase overhead, but was not independently audited here; our phases (including heavy passes) and GAPBS iterations are not necessarily equivalent units.

### Descriptive fit, winning-Δ splits and assumed traffic

Per graph, nonnegative least squares fits T(k,Δ) = c_edge × mean_source(Tideal_k) + c_sync(k) × mean_source(phases). One c_edge is shared across threads; each k has its own c_sync. Observations are all frozen E2 Δ/thread points; times are means of four source-wise medians. This is an in-sample descriptive fit, not a measurement of barrier time: the phase term can absorb bucket processing, memory, filtering, imbalance and other omitted costs. Both terms may be correlated. Percent splits divide fitted, not measured, time; measured minus fitted is shown separately. Leave-one-Δ-out RMSE refits on the other Δ values; it is unavailable with fewer than three Δ values or rank-deficient training designs. No new cluster measurements are used.

| Graph | Points / parameters | Rank | Scaled condition | R² | RMSE ms | Relative RMSE % | LODO RMSE ms | c_edge ns |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CTR | 24/7 | 7 | 5.705 | 0.991 | 23.947 | 4.698 | 33.522 | 20.317 |
| LJ | 18/7 | 7 | 5.117 | 0.985 | 42.570 | 7.710 | 76.180 | 15.111 |
| NY | 18/7 | 7 | 7.832 | 0.976 | 0.504 | 4.684 | 0.751 | 14.339 |
| OK | 18/7 | 7 | 4.416 | 0.984 | 84.377 | 7.932 | 154.863 | 8.938 |
| USA | 18/7 | 7 | 7.085 | 0.992 | 34.629 | 4.392 | 52.005 | 17.079 |
| grid2896 | 12/7 | 7 | 9.820 | 0.998 | 6.603 | 2.384 | N/A | 11.765 |
| kron23 | 24/7 | 7 | 3.412 | 0.942 | 114.706 | 13.691 | 186.894 | 14.083 |
| urand23 | 30/7 | 7 | 3.167 | 0.959 | 191.776 | 12.341 | 282.534 | 26.189 |

| Graph | t | Δ | Measured ms | Fitted ms | Work ms (%) | Phase/sync ms (%) | Residual ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| CTR | 1 | 8192 | 926.720 | 914.644 | 783.083 (85.616) | 131.560 (14.384) | 12.076 |
| CTR | 6 | 16384 | 327.972 | 334.433 | 139.236 (41.633) | 195.197 (58.367) | -6.461 |
| CTR | 12 | 32768 | 308.610 | 293.088 | 77.886 (26.574) | 215.202 (73.426) | 15.522 |
| LJ | 1 | 2048 | 1162.492 | 1126.655 | 1079.792 (95.840) | 46.863 (4.160) | 35.837 |
| LJ | 6 | 4096 | 291.744 | 278.248 | 190.273 (68.383) | 87.975 (31.617) | 13.496 |
| LJ | 12 | 4096 | 254.667 | 232.597 | 95.399 (41.015) | 137.198 (58.985) | 22.070 |
| NY | 1 | 8192 | 14.199 | 13.610 | 13.502 (99.212) | 0.107 (0.788) | 0.590 |
| NY | 6 | 16384 | 7.846 | 8.009 | 2.566 (32.041) | 5.443 (67.959) | -0.163 |
| NY | 12 | 16384 | 8.912 | 8.951 | 1.297 (14.490) | 7.654 (85.510) | -0.039 |
| OK | 1 | 512 | 2353.864 | 2314.572 | 2195.755 (94.867) | 118.818 (5.133) | 39.291 |
| OK | 6 | 1024 | 604.577 | 565.730 | 384.457 (67.958) | 181.273 (32.042) | 38.848 |
| OK | 12 | 1024 | 559.827 | 491.329 | 192.519 (39.183) | 298.810 (60.817) | 68.498 |
| USA | 1 | 16384 | 1407.254 | 1380.612 | 1203.958 (87.205) | 176.654 (12.795) | 26.642 |
| USA | 6 | 16384 | 517.520 | 551.180 | 200.186 (36.320) | 350.993 (63.680) | -33.660 |
| USA | 12 | 32768 | 497.617 | 501.875 | 112.367 (22.389) | 389.508 (77.611) | -4.258 |
| grid2896 | 1 | 131072 | 567.899 | 562.454 | 468.321 (83.264) | 94.133 (16.736) | 5.445 |
| grid2896 | 6 | 262144 | 177.502 | 169.535 | 87.322 (51.507) | 82.213 (48.493) | 7.967 |
| grid2896 | 12 | 262144 | 152.224 | 146.208 | 43.733 (29.912) | 102.475 (70.088) | 6.016 |
| kron23 | 1 | 1024 | 1787.821 | 1851.466 | 1851.466 (100.000) | 0.000 (0.000) | -63.645 |
| kron23 | 6 | 1024 | 521.226 | 477.507 | 308.584 (64.624) | 168.922 (35.376) | 43.720 |
| kron23 | 12 | 2048 | 486.874 | 307.083 | 155.442 (50.619) | 151.641 (49.381) | 179.791 |
| urand23 | 1 | 1024 | 3490.068 | 3543.332 | 3543.332 (100.000) | 0.000 (0.000) | -53.264 |
| urand23 | 6 | 1024 | 929.166 | 888.290 | 590.617 (66.489) | 297.672 (33.511) | 40.877 |
| urand23 | 12 | 1024 | 848.043 | 796.879 | 295.370 (37.066) | 501.509 (62.934) | 51.164 |

Effective traffic bound = mean_source(edges_scanned) × (8 + 64) bytes / mean-source-median time, in decimal GB/s. This assumes one 8-byte edge read plus a whole 64-byte destination-distance cache line per scan with no reuse. It is not measured DRAM traffic or a bound on all traffic: it omits, for example, bucket writes and extra coherence traffic. Values near or above the approximate 20 GB/s triad reference are consistent with cache reuse and/or memory pressure, not proof of bandwidth saturation or latency limitation.

| Graph | t | Δ | Assumed effective GB/s | /20 GB/s |
|---|---:|---:|---:|---:|
| CTR | 6 | 16384 | 8.996 | 0.450 |
| CTR | 12 | 32768 | 10.668 | 0.533 |
| LJ | 6 | 4096 | 18.625 | 0.931 |
| LJ | 12 | 4096 | 21.342 | 1.067 |
| NY | 6 | 16384 | 9.800 | 0.490 |
| NY | 12 | 16384 | 8.642 | 0.432 |
| OK | 6 | 1024 | 30.705 | 1.535 |
| OK | 12 | 1024 | 33.135 | 1.657 |
| USA | 6 | 16384 | 9.749 | 0.487 |
| USA | 12 | 32768 | 11.352 | 0.568 |
| grid2896 | 6 | 262144 | 18.048 | 0.902 |
| grid2896 | 12 | 262144 | 21.050 | 1.053 |
| kron23 | 6 | 1024 | 18.160 | 0.908 |
| kron23 | 12 | 2048 | 19.578 | 0.979 |
| urand23 | 6 | 1024 | 10.484 | 0.524 |
| urand23 | 12 | 1024 | 11.487 | 0.574 |

The computed LJ t12 traffic proxy is about 21 GB/s and USA about 11 GB/s; these are consistent with different traffic/cache behaviour, **not proof** of a latency or bandwidth bottleneck. NY’s graph plus distances can fit in the observed L3, unlike CTR/USA, but graph size, work per phase and synchronization also differ. The ~20 GB/s triad value is a proposal/reference value, not a bandwidth measurement from these runs.

### Perf and unrun load-imbalance work

No cycles/instructions/cache-miss counters were collected. The latest reviewer handoff restricted additions to existing data with **no new cluster runs**, so the earlier optional perf allocation was not added; compute-node perf availability was not newly tested. No counter-derived IPC or cache-miss claims are made. E3/Q3a schedule/imbalance measurements are not present in this agent’s dataset; the max-vertex ideal is not measured per-thread imbalance.

## Q4 — choosing Δ: H4 only partly holds

The best tested overhead α is thread-dependent: road+grid sequential winners use α=0.1; parallel winners generally prefer α=0.5, with **CTR t6 preferring α=0.25**. There is no universal α across graphs. The d_avg rule is not uniformly better than d_max: for kron23 sequential it is about **3.50×** slower than fastest versus **1.13×** for d_max. Thus the social-graph degree heuristic and road-graph overhead hypothesis hold only partially.

Each cell is **selected Δ / slowdown** relative to that mode’s fastest E1 run. Θ(W/d) values use W=w_max, exact m/n for d_avg, round half up, clamp to ≥1, and were timed at those exact integers. Overhead is `(expansions−reached)+(edges_scanned−E_dij)` averaged over sources; select the last passing power-of-two sweep point, allowing nonmonotonic overhead. **t12 overhead rules use t6 counters as a proxy**, not measured t12 work.

| Graph | Mode | W/d_max | W/d_avg | α=.1 | α=.25 | α=.5 | α=1 | α=2 |
|---|---|---|---|---|---|---|---|---|
| NY | seq | 4618 / 1.024× | 13377 / 1.147× | 1024 / 1.007× | 4096 / 1.024× | 16384 / 1.198× | 32768 / 1.477× | 65536 / 2.122× |
| NY | t6 | 4618 / 1.101× | 13377 / 1.003× | 512 / 1.800× | 4096 / 1.119× | 16384 / 1.000× | 32768 / 1.051× | 65536 / 1.244× |
| NY | t12 | 4618 / 1.197× | 13377 / 1.022× | 512 / 2.184× | 4096 / 1.235× | 16384 / 1.000× | 32768 / 1.006× | 65536 / 1.094× |
| LJ | seq | 13 / 1.082× | 18558 / 1.431× | 2048 / 1.007× | 8192 / 1.057× | 16384 / 1.159× | 16384 / 1.159× | 65536 / 2.190× |
| LJ | t6 | 13 / 2.074× | 18558 / 1.154× | 2048 / 1.001× | 8192 / 1.040× | 16384 / 1.124× | 16384 / 1.124× | 65536 / 1.791× |
| LJ | t12 | 13 / 3.199× | 18558 / 1.136× | 2048 / 1.007× | 8192 / 1.029× | 16384 / 1.112× | 16384 / 1.112× | 65536 / 1.730× |
| grid2896 | seq | 65536 / 1.000× | 65558 / 1.002× | 32768 / 1.003× | 131072 / 1.013× | 262144 / 1.045× | 262144 / 1.045× | 262144 / 1.045× |
| grid2896 | t6 | 65536 / 1.114× | 65558 / 1.114× | 32768 / 1.257× | 131072 / 1.029× | 262144 / 1.000× | 262144 / 1.000× | 262144 / 1.000× |
| grid2896 | t12 | 65536 / 1.275× | 65558 / 1.279× | 32768 / 1.548× | 131072 / 1.165× | 262144 / 1.000× | 262144 / 1.000× | 262144 / 1.000× |
| CTR | seq | 26752 / 1.111× | 88987 / 1.502× | 4096 / 1.000× | 16384 / 1.058× | 32768 / 1.146× | 65536 / 1.347× | 131072 / 1.782× |
| CTR | t6 | 26752 / 1.012× | 88987 / 1.189× | 4096 / 1.103× | 16384 / 1.000× | 32768 / 1.013× | 65536 / 1.101× | 131072 / 1.358× |
| CTR | t12 | 26752 / 1.009× | 88987 / 1.064× | 4096 / 1.317× | 16384 / 1.058× | 32768 / 1.000× | 65536 / 1.019× | 131072 / 1.167× |
| USA | seq | 40984 / 1.183× | 153064 / 1.934× | 4096 / 1.000× | 16384 / 1.047× | 32768 / 1.135× | 65536 / 1.336× | 131072 / 1.787× |
| USA | t6 | 40984 / 1.017× | 153064 / 1.425× | 4096 / 1.129× | 16384 / 1.000× | 32768 / 1.000× | 65536 / 1.084× | 131072 / 1.335× |
| USA | t12 | 40984 / 1.017× | 153064 / 1.219× | 4096 / 1.300× | 16384 / 1.076× | 32768 / 1.000× | 65536 / 1.022× | 131072 / 1.169× |
| kron23 | seq | 2 / 1.135× | 16766 / 3.500× | 128 / 1.004× | 256 / 1.044× | 512 / 1.165× | 1024 / 1.357× | 2048 / 1.724× |
| kron23 | t6 | 2 / 2.800× | 16766 / 3.343× | 128 / 1.000× | 256 / 1.003× | 512 / 1.067× | 1024 / 1.230× | 2048 / 1.553× |
| kron23 | t12 | 2 / 5.645× | 16766 / 1.292× | 4096 / 1.033× | 8192 / 1.128× | 16384 / 1.314× | 32768 / 1.763× | 65536 / 2.474× |
| urand23 | seq | 6554 / 1.018× | 16384 / 1.072× | 8192 / 1.027× | 16384 / 1.072× | 32768 / 1.157× | 131072 / 1.667× | 262144 / 1.963× |
| urand23 | t6 | 6554 / 1.017× | 16384 / 1.071× | 8192 / 1.024× | 16384 / 1.071× | 32768 / 1.155× | 131072 / 1.674× | 262144 / 1.967× |
| urand23 | t12 | 6554 / 1.021× | 16384 / 1.059× | 8192 / 1.021× | 16384 / 1.059× | 32768 / 1.158× | 131072 / 1.669× | 262144 / 1.965× |
| OK | seq | 8 / 1.082× | 3437 / 1.128× | 1024 / 1.008× | 2048 / 1.046× | 4096 / 1.258× | 8192 / 1.518× | 16384 / 2.136× |
| OK | t6 | 8 / 1.623× | 3437 / 1.078× | 1024 / 1.000× | 2048 / 1.020× | 4096 / 1.112× | 8192 / 1.350× | 16384 / 1.946× |
| OK | t12 | 8 / 2.113× | 3437 / 1.079× | 1024 / 1.000× | 2048 / 1.020× | 4096 / 1.125× | 8192 / 1.350× | 16384 / 1.904× |

Complete rule times and statuses: `e1_delta_sweep/q4_table.csv` and `q4_table.md`.

## Data quality, anomalies and scope

- Teammate’s E4 `ref_check.log` reportedly found approximately **600 corrupted LJ edges** dating from shared CSR creation. This external finding was not independently audited here. LJ runs remain Dijkstra-verified **on the same CSR file**; this establishes agreement on that input, not fidelity to the intended canonical LJ graph. No shared CSR was changed.
- The earlier raw-log disk-quota failure was storage-related, not a reported verification failure. Its approved FIFO recovery retried the full job; no sweep point was dropped. Recovered grid Δ=1 seq completed in 497.16 worker-seconds / 498.0 wrapper-seconds.
- No new raw phase logs, compressed logs, or partial phase logs are committed. Raw NY/LJ compatibility was tested exactly against the streaming reducer.
- Timings span multiple compute hosts and have only four sources/three repetitions; no confidence intervals or causal bottleneck identification are claimed. E1 and E2 independently measured times can differ and can change the winning neighbouring Δ.
- E3/E4 result directories, the protected owner clone and shared GAPBS data were not modified. Teammate context above is attribution, not a substitute for unavailable E3/E4 tables.

## Reproduce and inspect

```sh
PYTHONDONTWRITEBYTECODE=1 python3 analysis/e1_analysis.py
PYTHONDONTWRITEBYTECODE=1 python3 analysis/e2_analysis.py
PYTHONDONTWRITEBYTECODE=1 python3 analysis/summary.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s analysis
```

Key PNGs (matching PDF files are alongside them):

- [All-graph Q2 scaling](plots/e2_q2_scaling.png)
- [NY empty phases](plots/e1_NY_q1_empty_phases.png)
- [LJ Δ/time](plots/e1_LJ_q1_time.png)
- [urand23 Δ/time](plots/e1_urand23_q1_time.png)
- [USA ideals](plots/e2_USA_q3_ideal.png)
- [kron23 ideals](plots/e2_kron23_q3_ideal.png)
- [OK Δ/time](plots/e1_OK_q1_time.png)
- [LJ Q4 rules](plots/e1_LJ_q4_slowdown.png)
