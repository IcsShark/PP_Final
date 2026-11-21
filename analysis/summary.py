#!/usr/bin/env python3
"""Render the all-graph report only after both analyses are complete."""
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULES = ('W/d_max', 'W/d_avg', 'overhead_alpha=0.1', 'overhead_alpha=0.25',
         'overhead_alpha=0.5', 'overhead_alpha=1', 'overhead_alpha=2')


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
        '|' + '|'.join('---' for _ in headers) + '|'] +
        ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])


def render(graphs, q4, reductions, metrics, scaling, hardware):
    if not graphs or len(set(graphs)) != len(graphs):
        raise ValueError('missing or duplicate graph list')
    expected = {(g, t) for g in graphs for t in (1, 6, 12)}
    fastest = {(r['graph'], int(r['threads'])): r for r in q4 if r['rule'] == 'fastest'}
    if set(fastest) != expected or len(q4) != len(expected)*8:
        raise ValueError('incomplete Q4 results')
    choices = {(r['graph'], int(r['threads']), r['rule']): r for r in q4}
    if len(choices) != len(q4) or any((*key, rule) not in choices for key in expected for rule in RULES):
        raise ValueError('duplicate or missing Q4 rule')
    scaled = {(r['graph'], int(r['threads'])): r for r in scaling}
    if len(scaled) != len(scaling) or set(scaled) != {(g, t) for g in graphs for t in (1, 2, 4, 6, 8, 12)}:
        raise ValueError('incomplete E2 scaling results')
    lines = ['# E0–E2 experiment summary', '',
        'All eight E1/E2 graph queues completed. E3/Q3a and E4 are teammate-owned and were not run '
        'or merged by this agent. Tables below are generated from committed analysis CSVs by '
        '`python3 analysis/summary.py`; detailed input hashes are in each experiment’s `ANALYSIS_META.json`.', '',
        '## Measurement contract', '',
        '- Times are means over four fixed sources, each source taking the median of three timing-build '
        'repetitions. Stats-build times are never used as performance numbers. All rows are verified against Dijkstra.',
        '- All timing/stats allocations used whole-node `run -c 12`, including one-thread runs. '
        'E0 observed i5-10500/KVM guest topology **12 cores × 1 thread**, L3 **16 MiB**; '
        'six physical cores and a six-core SMT knee are not established by the guest report.',
        '- E1 holds each mode’s fastest variant/filter fixed when comparing Δ-selection rules. '
        'E2 freezes the globally fastest E1 OpenMP pair and tests the t6/t12 anchors and their sweep neighbours. '
        'Consequently E2’s t6 pair need not equal E1’s independent t6 winner.',
        '- New phase data were reduced through bounded FIFOs, never persisted as raw logs. '
        'The 208 legacy NY/LJ gzip paths/sizes/nanosecond mtimes were preserved. '
        'The quota failure and successful retry are documented in `e1_delta_sweep/STORAGE_RECOVERY.md`.', '',
        '## Q1 — Δ trades depth for redundant work', '',
        'All audited mean phase sweeps are nonincreasing. The timing minima generally occur between '
        'the work-heavy large-Δ and phase-heavy small-Δ extremes; **grid2896 OpenMP instead wins at the '
        'largest tested sweep Δ**, so its unconstrained optimum is not established. Merge can move an optimum '
        '(e.g. NY sequential 256→1024; LJ t6 all 2048→4096), but is not a universal speedup.', '',
        '### Fastest E1 Δ / milliseconds (variant/filter)', '']
    lines.append(table(['Graph', 'seq', 't6', 't12'], [[g] + [
        f'{fastest[g,t]["delta"]} / {float(fastest[g,t]["time_ms"]):.3f} '
        f'({fastest[g,t]["variant"]}/{fastest[g,t]["filter"]})' for t in (1, 6, 12)] for g in graphs]))
    lines += ['', '### Empty phases', '',
        'Primary definition: `expanded == 0`; `frontier == 0` is separate, not an expanded/frontier quotient. '
        'Initial shares below are ratios of mean empty to mean total phases across four sources at Δ=1, '
        'OpenMP t6. Attribution is `(empty_small−empty_large)/(phases_small−phases_large)` '
        'for all/pop, Δ=1→largest sweep Δ. Thus an initial empty fraction and a fraction of phase reduction '
        'are different quantities. Heavy passes are included. Zero logged empty frontiers does not imply '
        'zero filtering cost.', '']
    empty_rows = []
    for g in graphs:
        small = {(r['variant'], r['filter']): r for r in metrics if r['graph'] == g and
            r['algo'] == 'delta-omp' and int(r['threads']) == 6 and int(r['delta']) == 1}
        reduction = next(r for r in reductions if r['graph'] == g and r['algo'] == 'delta-omp'
            and r['variant'] == 'all' and r['filter'] == 'pop' and r['comparison'] == 'largest_sweep_delta')
        shares = [100*float(small[v,f]['empty_expanded'])/float(small[v,f]['phases'])
                  for v, f in (('all', 'pop'), ('lh', 'pop'), ('all', 'merge'), ('lh', 'merge'))]
        empty_rows.append([g] + [f'{v:.2f}%' for v in shares] + [reduction['larger_delta'],
            f'{100*float(reduction["empty_share"]):.2f}%'])
    lines += [table(['Graph', 'all/pop', 'lh/pop', 'all/merge', 'lh/merge', 'Largest Δ',
        'Empty attribution all/pop'], empty_rows), '',
        'Most phase reduction is from fewer **nonempty** phases, not empty phases. '
        'Full source-normalized work, expansions/reached and phases/buckets are in '
        '`e1_delta_sweep/q1_metrics.csv`; all per-pair comparisons are in `q1_phase_reduction.csv` '
        'and `q1_merge_best.csv` in the same directory.', '',
        '## Q2 — topology and measured scaling', '',
        'Social/random graphs have far more edges per phase than road graphs. NY peaks at t6 and '
        'slows at t12; LJ continues improving. This supports topology-dependent scaling, not a blanket '
        'claim that every social/synthetic graph scales identically. Each row below uses its fastest '
        'frozen E2 candidate Δ. Efficiency = speedup vs best E1 delta-seq / threads; the ideals use '
        'each row’s phase decomposition, while Q3 plots compare measured OMP-t1 at the **same Δ**.', '']
    lines.append(table(['Graph', 't', 'Δ', 'ms', 'vs seq', 'vs Dijkstra', 'Efficiency', 'Ideal max / no-max',
        'Phases', 'Edges/phase'], [[g, t, scaled[g,t]['delta'], f'{float(scaled[g,t]["time_ms"]):.3f}',
        f'{float(scaled[g,t]["speedup_seq"]):.3f}×', f'{float(scaled[g,t]["speedup_dijkstra"]):.3f}×',
        f'{100*float(scaled[g,t]["efficiency_seq"]):.1f}%',
        f'{float(scaled[g,t]["ideal_speedup"]):.3f} / {float(scaled[g,t]["ideal_no_max_speedup"]):.3f}',
        f'{float(scaled[g,t]["phases"]):.1f}', f'{float(scaled[g,t]["average_parallelism"]):.1f}']
        for g in graphs for t in (6, 12)]))
    lines += ['', '## Q3 — work-only headroom, phase costs and memory', '',
        'Both work-only ideals are almost linear, far above measured speedups. The maximum-vertex '
        'term alone therefore does not explain the gap. A phase-aware model is fitted below from '
        '**existing data only**. Its phase/sync component is not a direct barrier-time measurement. '
        'In particular, kron23 has a large winning-t12 residual despite a seemingly good aggregate R²; '
        'do not interpret its fitted split as an accurate physical decomposition.', '',
        'Teammate-provided E4 context reports road-graph phase counts roughly **40×** GAPBS iterations. '
        'This is consistent with substantial per-phase overhead, but was not independently audited here; '
        'our phases (including heavy passes) and GAPBS iterations are not necessarily equivalent units.', '',
        hardware.replace('# Q3 work/phase model and effective bandwidth',
                         '### Descriptive fit, winning-Δ splits and assumed traffic').strip(), '',
        'The computed LJ t12 traffic proxy is about 21 GB/s and USA about 11 GB/s; '
        'these are consistent with different traffic/cache behaviour, **not proof** of a latency '
        'or bandwidth bottleneck. NY’s graph plus distances can fit in the observed L3, unlike CTR/USA, '
        'but graph size, work per phase and synchronization also differ. The ~20 GB/s triad value is '
        'a proposal/reference value, not a bandwidth measurement from these runs.', '',
        '### Perf and unrun load-imbalance work', '',
        'No cycles/instructions/cache-miss counters were collected. The latest reviewer handoff '
        'restricted additions to existing data with **no new cluster runs**, so the earlier optional '
        'perf allocation was not added; compute-node perf availability was not newly tested. '
        'No counter-derived IPC or cache-miss claims are made. E3/Q3a schedule/imbalance measurements '
        'are not present in this agent’s dataset; the max-vertex ideal is not measured per-thread imbalance.', '',
        '## Q4 — choosing Δ: H4 only partly holds', '',
        'The best tested overhead α is thread-dependent: road+grid sequential winners use α=0.1; '
        'parallel winners generally prefer α=0.5, with **CTR t6 preferring α=0.25**. '
        'There is no universal α across graphs. The d_avg rule is not uniformly better than d_max: '
        'for kron23 sequential it is about **3.50×** slower than fastest versus **1.13×** for d_max. '
        'Thus the social-graph degree heuristic and road-graph overhead hypothesis hold only partially.', '',
        'Each cell is **selected Δ / slowdown** relative to that mode’s fastest E1 run. '
        'Θ(W/d) values use W=w_max, exact m/n for d_avg, round half up, clamp to ≥1, and were timed '
        'at those exact integers. Overhead is `(expansions−reached)+(edges_scanned−E_dij)` averaged '
        'over sources; select the last passing power-of-two sweep point, allowing nonmonotonic overhead. '
        '**t12 overhead rules use t6 counters as a proxy**, not measured t12 work.', '']
    q4_rows = []
    for g in graphs:
        for t in (1, 6, 12):
            cells = []
            for rule in RULES:
                r = choices[g,t,rule]
                cells.append(f'{r["delta"]} / {float(r["slowdown"]):.3f}×' if r['status'] == 'ok' else 'N/A')
            q4_rows.append([g, 'seq' if t == 1 else f't{t}'] + cells)
    lines += [table(['Graph', 'Mode', 'W/d_max', 'W/d_avg', 'α=.1', 'α=.25', 'α=.5', 'α=1', 'α=2'], q4_rows), '',
        'Complete rule times and statuses: `e1_delta_sweep/q4_table.csv` and `q4_table.md`.', '',
        '## Data quality, anomalies and scope', '',
        '- Teammate’s E4 `ref_check.log` reportedly found approximately **600 corrupted LJ edges** '
        'dating from shared CSR creation. This external finding was not independently audited here. '
        'LJ runs remain Dijkstra-verified **on the same CSR file**; this establishes agreement on that '
        'input, not fidelity to the intended canonical LJ graph. No shared CSR was changed.',
        '- The earlier raw-log disk-quota failure was storage-related, not a reported verification '
        'failure. Its approved FIFO recovery retried the full job; no sweep point was dropped. '
        'Recovered grid Δ=1 seq completed in 497.16 worker-seconds / 498.0 wrapper-seconds.',
        '- No new raw phase logs, compressed logs, or partial phase logs are committed. '
        'Raw NY/LJ compatibility was tested exactly against the streaming reducer.',
        '- Timings span multiple compute hosts and have only four sources/three repetitions; no '
        'confidence intervals or causal bottleneck identification are claimed. E1 and E2 independently '
        'measured times can differ and can change the winning neighbouring Δ.',
        '- E3/E4 result directories, the protected owner clone and shared GAPBS data were not modified. '
        'Teammate context above is attribution, not a substitute for unavailable E3/E4 tables.', '',
        '## Reproduce and inspect', '',
        '```sh\nPYTHONDONTWRITEBYTECODE=1 python3 analysis/e1_analysis.py\n'
        'PYTHONDONTWRITEBYTECODE=1 python3 analysis/e2_analysis.py\n'
        'PYTHONDONTWRITEBYTECODE=1 python3 analysis/summary.py\n'
        'PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s analysis\n```', '',
        'Key PNGs (matching PDF files are alongside them):', '',
        '- [All-graph Q2 scaling](plots/e2_q2_scaling.png)',
        '- [NY empty phases](plots/e1_NY_q1_empty_phases.png)',
        '- [LJ Δ/time](plots/e1_LJ_q1_time.png)',
        '- [urand23 Δ/time](plots/e1_urand23_q1_time.png)',
        '- [USA ideals](plots/e2_USA_q3_ideal.png)',
        '- [kron23 ideals](plots/e2_kron23_q3_ideal.png)',
        '- [OK Δ/time](plots/e1_OK_q1_time.png)',
        '- [LJ Q4 rules](plots/e1_LJ_q4_slowdown.png)', '']
    return '\n'.join(lines)


def main():
    out = ROOT / 'results'
    manifest = json.loads((out / 'e1_delta_sweep/jobs.json').read_text())
    for name in ('e1_delta_sweep', 'e2_scaling'):
        if json.loads((out / name / 'ANALYSIS_META.json').read_text())['pending']:
            raise ValueError('analysis still has pending graphs')
    def read(name):
        with (out / name).open() as stream:
            return list(csv.DictReader(stream))
    text = render(list(manifest['profiles']), read('e1_delta_sweep/q4_table.csv'),
        read('e1_delta_sweep/q1_phase_reduction.csv'), read('e1_delta_sweep/q1_metrics.csv'),
        read('e2_scaling/scaling_table.csv'), (out / 'e2_scaling/q3_hardware.md').read_text())
    (out / 'SUMMARY.md').write_text(text)
    print(f'PASS: SUMMARY.md generated for {len(manifest["profiles"])} graphs')


if __name__ == '__main__':
    main()
