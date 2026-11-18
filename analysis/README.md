# E1 analysis

On the VM, with Python 3 and Matplotlib installed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 analysis/e1_analysis.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s analysis
```

Synchronize completed result CSVs **and their `.done` markers**, profiles, and
`results/e1_delta_sweep/phase_summaries/*.json` from the cluster before rerunning.
The analysis selects only graphs whose full manifest grid has completed. It refuses
unverified rows, mismatched CSV digests, missing repetitions/sources, and reduced
phase counts/edge totals that disagree with stats CSVs. Partial graphs are reported
as pending. Plots that require phase summaries are withheld until those summaries
are complete. No phase logs need to be copied to the VM.

## Aggregation and interpretation

- Performance: take each source's median of its three timing-build repetitions,
  then the arithmetic mean across the four fixed sources. Stats-build times are
  never used as performance measurements.
- Work/depth: average four source values. `edges_scanned / E_dij` uses the
  **matching source's** stats-build Dijkstra edge count. `expansions / reached`
  and `phases / buckets` are likewise ratios computed per source before averaging.
- Stats exist for sequential and OpenMP t6, not t12. Work/depth plots therefore
  show seq/t6. For Q4's t12 overhead-based selection, t6 counters are an explicitly
  labeled proxy, not a measurement of t12 work.
- The primary empty-phase definition is **`expanded == 0`**, not a quotient:
  no frontier vertex was expanded. `frontier == 0` is counted separately. Merge
  can remove stale entries and skip an empty frontier before logging a phase, so
  zero logged empty-frontier phases does **not** mean there was no filtering work.
  `edges == 0` is an additional diagnostic: a light/heavy pass can expand vertices
  but scan zero edges, so it is distinct from the primary definition.
- Phase-reduction attribution compares the smallest sweep Δ to both the largest
  sweep Δ and each variant/filter's fastest timing Δ. The fraction attributable
  to empty phases is `(empty_small - empty_large) / (phases_small - phases_large)`.
  Nonempty-phase reduction is the residual; neither fraction is clipped. A zero
  denominator is reported as unavailable. Heavy passes are included in total phases.
- Merge optimum comparisons are separate for each algorithm/thread count and
  variant, rather than conflating changes in variant or thread count.

## Q4 choices

For each graph and execution mode (seq/t6/t12), choose the globally fastest
measured Δ/variant/filter and hold that variant/filter fixed when comparing rules.
This isolates Δ selection from changing the algorithm variant.

- `W/d_max` and `W/d_avg` use `W=w_max`, `d_avg=m/n` without printed-profile
  rounding, then round half up to an integer and clamp to at least one. These
  selected Δ values have exact timing runs, not nearest-power-of-two substitutes.
- For each source, overhead is `(expansions-reached)+(edges_scanned-E_dij)`.
  Average the four source overheads, and choose the **last passing Δ** from the
  sorted power-of-two sweep with overhead `<= alpha*(n+m)`. Extra W/d rule Δ values
  are not added to this candidate set. Nonmonotonic overhead is allowed; the walk
  does not stop at the first failing point. If no point passes, output N/A.
- Slowdown is the selected Δ's mean source-median time divided by the globally
  fastest mean source-median time for that execution mode.

Outputs: `q4_table.{csv,md}`, `q1_metrics.csv`, `q1_phase_reduction.csv`,
`q1_merge_best.csv`, `q1_findings.md`, and `ANALYSIS_META.json` under `results/e1_delta_sweep/`.
Each complete graph gets time, work/depth, empty-phase, and Q4-slowdown figures
as **PDF + PNG** under `results/plots/e1_<graph>_*.{pdf,png}`.

## Compute-side phase reduction

`analysis/e1_phase_reduce.py` streams the gzipped phase logs and retains only
small per-run summaries. The E1 worker invokes it **after kernel measurements**
inside its existing whole-node allocation: its own new phase logs first, then a
bounded NY/LJ/current-graph backlog. It uses a 90-second soft budget, 24-file limit,
and a 150-second subprocess timeout, shortened to leave 30 seconds before the
worker's outer 1190-second deadline (and skipped with under five seconds available).
Individual files are atomic cache units. Reduction
failure is recorded in `phase_reduction.failed` without stopping verified SSSP jobs;
incomplete caches are retried. Original phase logs remain untouched in
`~/devin/results_raw/e1/` and are never committed.

The login driver is not restarted or changed and no second job is submitted.
Future stats workers reduce their own logs automatically; rerun the VM analysis
after synchronizing the new CSVs/markers/summaries. `ANALYSIS_META.json` records
input hashes (CSVs, profiles and phase summaries), manifest hash, analysis source
hash and completeness.
