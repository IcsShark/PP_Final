# Dataset sources

All files can be downloaded with `scripts/fetch-datasets.sh`.

Check with `md5sum -c` (see bottom or `md5sums.txt`).

## Road graphs

### dimacs9_USA-road-d.USA.gr.gz — full USA, distance weights
- url: https://web.archive.org/web/2020id_/http://www.dis.uniroma1.it/challenge9/data/USA-road-d/USA-road-d.USA.gr.gz
- original: 9th DIMACS Implementation Challenge (www.diag.uniroma1.it/challenge9; the original site is unreachable, so this comes from Wayback)
- header: `p sp 23947347 58333344` (n = 23,947,347, directed arcs = 58,333,344)
- format: DIMACS `.gr` (`a u v w`, 1-indexed)
- checked: arc count = header m, all ids in [1, n], no self-loops, all weights ≥ 1, max weight 368,855
- md5: 8e741894569c20267ac59be6dcf57a83
- used by: GAP Benchmark Suite (`road` = this graph; SuiteSparse `GAP/GAP-road` is the same graph re-packaged); Dong et al. SPAA'21 "RoadUSA (USA)", 24M / 58M

### dimacs9_USA-road-d.CTR.gr.gz — Central USA, distance weights
- url: https://web.archive.org/web/2020id_/http://www.dis.uniroma1.it/challenge9/data/USA-road-d/USA-road-d.CTR.gr.gz
- header: `p sp 14081816 34292496`
- checked: arc count = header m, all ids in [1, n], no self-loops, all weights ≥ 1, max weight 214,013
- md5: 2554efa6619020a3c4c70d6db10890a3
- used by: GPU SSSP papers (Gunrock and follow-ups) as `road_central`

### dimacs9_USA-road-d.NY.gr.gz — New York, distance weights (small, for scaling experiments)
- url: https://web.archive.org/web/2020id_/http://www.dis.uniroma1.it/challenge9/data/USA-road-d/USA-road-d.NY.gr.gz
- header: `p sp 264346 733846`
- checked: arc count = header m, all ids in [1, n], no self-loops, all weights ≥ 1, max weight 36,946
- md5: 66f4bfb48892ab46ca8e213e4034f35f

## Social graphs (unweighted; Dong et al. use uniform random weights in [1, 2^18))

### snap_soc-LiveJournal1.txt.gz — LiveJournal (Dong et al. "LJ")
- url: https://snap.stanford.edu/data/soc-LiveJournal1.txt.gz
- header: Nodes 4,847,571, Edges 68,993,773 (directed edge list), which matches Dong et al. "4M / 68M"
- format: tab-separated `u v` per line, `#` comment header, ids 0-indexed and contiguous (0..4,847,570)
- checked: 68,993,773 lines = header, no duplicate directed edges, **518,382 self-loops**, 42,851,237 distinct undirected pairs (excluding loops), so symmetrizing gives 85,702,474 directed edges
- md5: 54fdcca873c051681e24972a39c81560

### snap_com-orkut.ungraph.txt.gz — Orkut (Dong et al. "OK")
- url: https://snap.stanford.edu/data/bigdata/communities/com-orkut.ungraph.txt.gz
- header: Nodes 3,072,441, Edges 117,185,083 (undirected; 234M after symmetrizing), which matches Dong et al. "3M / 234M"
- format: tab-separated `u v` per line, `#` comment header, each undirected pair stored once (u < v)
- checked: 117,185,083 lines = header, no self-loops, no duplicates; ids are **1-indexed and not contiguous**: range 1..3,072,626 but only 3,072,441 distinct, so remap ids before building CSR
- md5: 056746d96b9a980f610007e59a9a4e35

## Synthetic graphs (generated, not downloaded)
- Kron / RMAT, Urand (Erdős–Rényi), 2D grid
- generator: GAP Benchmark Suite (`-g` kron, `-u` urand); 2D grid by our own script
- scale: ~2^22–2^24 vertices (limited by 12 GB RAM on compute nodes)
- weights: uniform random integers, same range as social graphs
- purpose: controlled experiments (diameter, degree skew, weight distribution)


## References

### Comparison baselines (papers that evaluate on these datasets)
- Dong, Gu, Sun, Zhang. Efficient Stepping Algorithms and Implementations for Parallel Shortest Paths. SPAA 2021. https://arxiv.org/abs/2105.06145
  - uses: USA, LiveJournal, Orkut (sizes verified against Table 4)
- Beamer, Asanović, Patterson. The GAP Benchmark Suite. arXiv 2015. https://arxiv.org/abs/1508.03619 ; SuiteSparse GAP-road: https://sparse.tamu.edu/GAP/GAP-road
  - uses: USA (GAP `road` = USA-road-d.USA)
- Wang et al. Gunrock: A High-Performance Graph Processing Library on the GPU. PPoPP 2016.
  - uses: CTR as `road_central`, possibly LiveJournal / Orkut
  - **not directly verified**: inferred from a later GPU paper (arXiv 2012.07990) that reuses Gunrock's datasets; Gunrock's copies come from SuiteSparse and may not carry the original DIMACS weights. Check the Gunrock paper before comparing numbers.

### Dataset and algorithm sources (not used for comparison)
- Meyer, Sanders. Δ-stepping: a parallelizable shortest path algorithm. Journal of Algorithms 49(1), 2003. (algorithm)
- Demetrescu, Goldberg, Johnson (eds.). The Shortest Path Problem: Ninth DIMACS Implementation Challenge. AMS, 2009. http://www.diag.uniroma1.it/challenge9/ (USA, CTR, NY)
- Leskovec, Krevl. SNAP Datasets: Stanford Large Network Dataset Collection. 2014. https://snap.stanford.edu/data (LiveJournal, Orkut)
- Backstrom, Huttenlocher, Kleinberg, Lan. Group Formation in Large Social Networks. KDD 2006. (LiveJournal)
- Yang, Leskovec. Defining and Evaluating Network Communities based on Ground-truth. ICDM 2012. (Orkut)

### Note
- NY is not used by any comparison baseline; it is included only as the small end of the road-graph scaling series (NY → CTR → USA).



## md5sum -c
```
8e741894569c20267ac59be6dcf57a83  dimacs9_USA-road-d.USA.gr.gz
2554efa6619020a3c4c70d6db10890a3  dimacs9_USA-road-d.CTR.gr.gz
66f4bfb48892ab46ca8e213e4034f35f  dimacs9_USA-road-d.NY.gr.gz
54fdcca873c051681e24972a39c81560  snap_soc-LiveJournal1.txt.gz
056746d96b9a980f610007e59a9a4e35  snap_com-orkut.ungraph.txt.gz
```
