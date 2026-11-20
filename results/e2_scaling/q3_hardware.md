# Q3 work/phase model and effective bandwidth

Per graph, nonnegative least squares fits T(k,Δ) = c_edge × mean_source(Tideal_k) + c_sync(k) × mean_source(phases). One c_edge is shared across threads; each k has its own c_sync. Observations are all frozen E2 Δ/thread points; times are means of four source-wise medians. This is an in-sample descriptive fit, not a measurement of barrier time: the phase term can absorb bucket processing, memory, filtering, imbalance and other omitted costs. Both terms may be correlated. Percent splits divide fitted, not measured, time; measured minus fitted is shown separately. Leave-one-Δ-out RMSE refits on the other Δ values; it is unavailable with fewer than three Δ values or rank-deficient training designs. No new cluster measurements are used.

| Graph | Points / parameters | Rank | Scaled condition | R² | RMSE ms | Relative RMSE % | LODO RMSE ms | c_edge ns |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CTR | 24/7 | 7 | 5.705 | 0.991 | 23.947 | 4.698 | 33.522 | 20.317 |
| LJ | 18/7 | 7 | 5.117 | 0.985 | 42.570 | 7.710 | 76.180 | 15.111 |
| NY | 18/7 | 7 | 7.832 | 0.976 | 0.504 | 4.684 | 0.751 | 14.339 |
| USA | 18/7 | 7 | 7.085 | 0.992 | 34.629 | 4.392 | 52.005 | 17.079 |
| grid2896 | 12/7 | 7 | 9.820 | 0.998 | 6.603 | 2.384 | N/A | 11.765 |
| kron23 | 24/7 | 7 | 3.412 | 0.942 | 114.706 | 13.691 | 186.894 | 14.083 |

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
| USA | 1 | 16384 | 1407.254 | 1380.612 | 1203.958 (87.205) | 176.654 (12.795) | 26.642 |
| USA | 6 | 16384 | 517.520 | 551.180 | 200.186 (36.320) | 350.993 (63.680) | -33.660 |
| USA | 12 | 32768 | 497.617 | 501.875 | 112.367 (22.389) | 389.508 (77.611) | -4.258 |
| grid2896 | 1 | 131072 | 567.899 | 562.454 | 468.321 (83.264) | 94.133 (16.736) | 5.445 |
| grid2896 | 6 | 262144 | 177.502 | 169.535 | 87.322 (51.507) | 82.213 (48.493) | 7.967 |
| grid2896 | 12 | 262144 | 152.224 | 146.208 | 43.733 (29.912) | 102.475 (70.088) | 6.016 |
| kron23 | 1 | 1024 | 1787.821 | 1851.466 | 1851.466 (100.000) | 0.000 (0.000) | -63.645 |
| kron23 | 6 | 1024 | 521.226 | 477.507 | 308.584 (64.624) | 168.922 (35.376) | 43.720 |
| kron23 | 12 | 2048 | 486.874 | 307.083 | 155.442 (50.619) | 151.641 (49.381) | 179.791 |

Effective traffic bound = mean_source(edges_scanned) × (8 + 64) bytes / mean-source-median time, in decimal GB/s. This assumes one 8-byte edge read plus a whole 64-byte destination-distance cache line per scan with no reuse. It is not measured DRAM traffic or a bound on all traffic: it omits, for example, bucket writes and extra coherence traffic. Values near or above the approximate 20 GB/s triad reference are consistent with cache reuse and/or memory pressure, not proof of bandwidth saturation or latency limitation.

| Graph | t | Δ | Assumed effective GB/s | /20 GB/s |
|---|---:|---:|---:|---:|
| CTR | 6 | 16384 | 8.996 | 0.450 |
| CTR | 12 | 32768 | 10.668 | 0.533 |
| LJ | 6 | 4096 | 18.625 | 0.931 |
| LJ | 12 | 4096 | 21.342 | 1.067 |
| NY | 6 | 16384 | 9.800 | 0.490 |
| NY | 12 | 16384 | 8.642 | 0.432 |
| USA | 6 | 16384 | 9.749 | 0.487 |
| USA | 12 | 32768 | 11.352 | 0.568 |
| grid2896 | 6 | 262144 | 18.048 | 0.902 |
| grid2896 | 12 | 262144 | 21.050 | 1.053 |
| kron23 | 6 | 1024 | 18.160 | 0.908 |
| kron23 | 12 | 2048 | 19.578 | 0.979 |
