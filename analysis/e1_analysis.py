#!/usr/bin/env python3
"""Rerunnable Q1/Q4 analysis of complete E1 graphs; see analysis/README.md."""
import argparse
import collections
import csv
import hashlib
import json
import math
import pathlib
import statistics
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/e1_delta_sweep'
PLOTS = ROOT / 'results/plots'
PAIRS = [('all', 'pop'), ('all', 'merge'), ('lh', 'pop'), ('lh', 'merge')]
COLORS = ['#1769aa', '#d05a17', '#27834d', '#9555a4']
ALPHAS = (0.1, 0.25, 0.5, 1, 2)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rounded_rules(profile):
    return [max(1, math.floor(value + 0.5)) for value in
            (profile['w_max'] / profile['d_max'], profile['w_max'] * profile['n'] / profile['m'])]


def last_passing(sweep, overhead, limit):
    passing = [d for d in sorted(sweep) if overhead[d] <= limit]
    return passing[-1] if passing else None


def write_csv(path, rows):
    if not rows:
        path.write_text('')
        return
    with path.open('w', newline='') as f:
        fields = list(dict.fromkeys(name for row in rows for name in row))
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


class Data:
    def __init__(self, out=OUT, root=ROOT):
        self.out, self.root = out, root
        self.manifest = json.loads((out / 'jobs.json').read_text())
        order = list(self.manifest['profiles'])
        self.graphs = [g for g in order if all((out / (j['id'] + '.done')).exists() and
                      (out / (j['id'] + '.csv')).exists() for j in self.manifest['jobs'] if j['graph'] == g)]
        self.pending = [g for g in order if g not in self.graphs]
        if not self.graphs:
            raise ValueError('no complete graphs; synchronize CSVs and .done markers first')
        self.inputs, self.stats, self.dij, timings = {}, {}, {}, collections.defaultdict(list)
        for job in self.manifest['jobs']:
            if job['graph'] not in self.graphs:
                continue
            path = out / (job['id'] + '.csv')
            self.inputs[str(path.relative_to(root))] = sha(path)
            marker = json.loads(path.with_suffix('.done').read_text())
            if marker['csv_sha256'] != sha(path):
                raise ValueError(f'CSV digest mismatch: {path}')
            with path.open() as f:
                rows = list(csv.DictReader(f))
            if len(rows) != len(job['sources']) * len(job['deltas']) * job['reps']:
                raise ValueError(f'incomplete CSV: {path}')
            for row in rows:
                if row['verified'] != '1' or not math.isfinite(float(row['time_ms'])):
                    raise ValueError(f'unverified or invalid row: {path}')
                key = (row['graph'], row['algo'], int(row['threads']), row['variant'],
                       row['filter'], int(row['delta']), int(row['source']))
                if job['kind'] == 'timing':
                    if row['stats_build'] != '0':
                        raise ValueError('stats timing cannot be used for performance')
                    timings[key].append(float(row['time_ms']))
                elif job['kind'] == 'stats':
                    if row['stats_build'] != '1' or key in self.stats:
                        raise ValueError('invalid or duplicate stats row')
                    self.stats[key] = row
                elif job['kind'] == 'dijkstra_stats':
                    self.dij[(row['graph'], int(row['source']))] = int(row['edges_scanned'])
        per_source = collections.defaultdict(list)
        for key, values in timings.items():
            if len(values) != 3:
                raise ValueError(f'expected three timing repetitions: {key}')
            per_source[key[:-1]].append(statistics.median(values))
        if any(len(v) != 4 for v in per_source.values()):
            raise ValueError('expected four timing sources')
        self.times = {k: statistics.mean(v) for k, v in per_source.items()}
        self.phases = {}
        for path in sorted((out / 'phase_summaries').glob('*.json')):
            self.inputs[str(path.relative_to(root))] = sha(path)
            payload = json.loads(path.read_text())
            for row in payload['rows']:
                key = (row['graph'], row['algo'], int(row['threads']), row['variant'],
                       row['filter'], int(row['delta']), int(row['source']))
                if key not in self.stats:
                    continue
                if key in self.phases:
                    raise ValueError(f'duplicate phase reduction: {key}')
                stats = self.stats[key]
                for reduced, original in (('phases', 'phases'), ('edges_sum', 'edges_scanned'),
                                          ('heavy_phases', 'heavy_passes')):
                    if row[reduced] != int(stats[original]):
                        raise ValueError(f'phase reduction disagrees with CSV: {key} {reduced}')
                self.phases[key] = row
        grouped = collections.defaultdict(list)
        for key, row in self.stats.items():
            edij = self.dij[(key[0], key[-1])]
            if edij <= 0 or int(row['reached']) <= 0 or int(row['buckets']) <= 0:
                raise ValueError(f'invalid normalization denominator: {key}')
            metrics = dict(phases=int(row['phases']),
                           edge_ratio=int(row['edges_scanned']) / edij,
                           expansion_ratio=int(row['expansions']) / int(row['reached']),
                           phases_per_bucket=int(row['phases']) / int(row['buckets']),
                           overhead=(int(row['expansions']) - int(row['reached']) +
                                     int(row['edges_scanned']) - edij))
            if key in self.phases:
                for counter in ('empty_frontier', 'empty_expanded', 'empty_edges'):
                    metrics[counter] = self.phases[key][counter]
            grouped[key[:-1]].append(metrics)
        self.metrics = {}
        for key, values in grouped.items():
            if len(values) != 4:
                raise ValueError(f'expected four stats sources: {key}')
            names = set.intersection(*(set(v) for v in values))
            self.metrics[key] = {name: statistics.mean(v[name] for v in values) for name in sorted(names)}

    def profile(self, graph):
        path = self.root / 'results/profile' / (graph + '.json')
        self.inputs[str(path.relative_to(self.root))] = sha(path)
        return json.loads(path.read_text())

    def best(self, graph, algo, threads, pair=None):
        candidates = [(ms, key) for key, ms in self.times.items() if key[:3] == (graph, algo, threads)
                      and (pair is None or key[3:5] == pair)]
        return min(candidates)


def q4_rows(data):
    rows = []
    for graph in data.graphs:
        p = data.profile(graph)
        for algo, threads in (('delta-seq', 1), ('delta-omp', 6), ('delta-omp', 12)):
            best_ms, best_key = data.best(graph, algo, threads)
            variant, filt = best_key[3:5]
            st = 1 if algo == 'delta-seq' else 6
            overhead = {d: data.metrics[(graph, algo, st, variant, filt, d)]['overhead']
                        for d in data.manifest['profiles'][graph]['sweep']}
            rules = [('fastest', best_key[-1])]
            rules += list(zip(('W/d_max', 'W/d_avg'), rounded_rules(p)))
            rules += [(f'overhead_alpha={alpha:g}', last_passing(list(overhead), overhead,
                        alpha * (p['n'] + p['m']))) for alpha in ALPHAS]
            for name, delta in rules:
                ms = data.times[(graph, algo, threads, variant, filt, delta)] if delta else None
                rows.append(dict(graph=graph, algo=algo, threads=threads, variant=variant, filter=filt,
                                 rule=name, delta=delta, time_ms=ms,
                                 slowdown=ms / best_ms if ms is not None else None,
                                 fastest_delta=best_key[-1], fastest_time_ms=best_ms,
                                 stats_threads=st, status='ok' if delta else 'no_passing_sweep_delta'))
    return rows


def phase_findings(data):
    reductions, merge = [], []
    for graph in data.graphs:
        sweep = data.manifest['profiles'][graph]['sweep']
        for algo, threads in (('delta-seq', 1), ('delta-omp', 6)):
            for variant, filt in PAIRS:
                best_ms, key = data.best(graph, algo, threads, (variant, filt))
                small = data.metrics[(graph, algo, threads, variant, filt, sweep[0])]
                for comparison, delta in (('largest_sweep_delta', sweep[-1]), ('best_pair_delta', key[-1])):
                    large = data.metrics[(graph, algo, threads, variant, filt, delta)]
                    if 'empty_expanded' not in small or 'empty_expanded' not in large:
                        continue
                    reduction = small['phases'] - large['phases']
                    empty_reduction = small['empty_expanded'] - large['empty_expanded']
                    reductions.append(dict(graph=graph, algo=algo, threads=threads, variant=variant,
                        filter=filt, comparison=comparison, small_delta=sweep[0], larger_delta=delta,
                        phases_small=small['phases'], phases_large=large['phases'],
                        empty_expanded_small=small['empty_expanded'], empty_expanded_large=large['empty_expanded'],
                        phase_reduction=reduction, empty_phase_reduction=empty_reduction,
                        nonempty_phase_reduction=reduction-empty_reduction,
                        empty_share=empty_reduction / reduction if reduction else None))
        for algo, threads in (('delta-seq', 1), ('delta-omp', 6), ('delta-omp', 12)):
            for variant in ('all', 'lh'):
                pm, pk = data.best(graph, algo, threads, (variant, 'pop'))
                mm, mk = data.best(graph, algo, threads, (variant, 'merge'))
                merge.append(dict(graph=graph, algo=algo, threads=threads, variant=variant,
                                  pop_best_delta=pk[-1], pop_time_ms=pm, merge_best_delta=mk[-1],
                                  merge_time_ms=mm, best_delta_moved=pk[-1] != mk[-1]))
    return reductions, merge


def save(fig, name):
    fig.savefig(PLOTS / (name + '.png'), dpi=160, bbox_inches='tight')
    fig.savefig(PLOTS / (name + '.pdf'), bbox_inches='tight')
    plt.close(fig)


def decorate(ax, ylabel, logy=False):
    ax.set_xscale('log', base=2)
    if logy:
        ax.set_yscale('log')
    ax.set_xlabel('Δ')
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.22)


def plots(data, q4):
    PLOTS.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    for graph in data.graphs:
        ds = data.manifest['profiles'][graph]['deltas']
        fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout='constrained')
        for ax, (variant, filt) in zip(axes.flat, PAIRS):
            for algo, t, color, label in (('delta-seq', 1, COLORS[0], 'sequential'),
                                         ('delta-omp', 6, COLORS[1], 'OpenMP t=6'),
                                         ('delta-omp', 12, COLORS[2], 'OpenMP t=12')):
                values = [data.times[(graph, algo, t, variant, filt, d)] for d in ds]
                ax.plot(ds, values, marker='.', color=color, label=label)
            ax.set_title(f'{variant} / {filt}')
            decorate(ax, 'Mean source-median time (ms)', True)
            ax.legend(fontsize=8)
        fig.suptitle(f'{graph} · Δ vs kernel time · four sources, three repetitions · whole node')
        save(fig, f'e1_{graph}_q1_time')
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
        names = [('phases', 'Phases', True), ('edge_ratio', 'Edges scanned / source Dijkstra edges', True),
                 ('expansion_ratio', 'Expansions / reached vertices', True),
                 ('phases_per_bucket', 'Phases / buckets', False)]
        for ax, (metric, title, logy) in zip(axes.flat, names):
            for (variant, filt), color in zip(PAIRS, COLORS):
                for algo, t, style, label in (('delta-seq', 1, '--', 'seq'), ('delta-omp', 6, '-', 'omp6')):
                    values = [data.metrics[(graph, algo, t, variant, filt, d)][metric] for d in ds]
                    ax.plot(ds, values, linestyle=style, color=color, label=f'{variant}/{filt} {label}')
            decorate(ax, title, logy)
        axes[0, 0].legend(fontsize=7, ncol=2)
        fig.suptitle(f'{graph} · Work and depth · means of per-source normalized stats (not timing data)')
        save(fig, f'e1_{graph}_q1_work_depth')
        phase_keys = [k for k in data.stats if k[0] == graph]
        if all(k in data.phases for k in phase_keys):
            fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout='constrained')
            for ax, (algo, t, variant) in zip(axes.flat, [('delta-seq', 1, 'all'), ('delta-omp', 6, 'all'),
                                                        ('delta-seq', 1, 'lh'), ('delta-omp', 6, 'lh')]):
                for filt, color in [('pop', COLORS[0]), ('merge', COLORS[1])]:
                    for metric, style, label in [('phases', '-', 'total'), ('empty_expanded', '--', 'expanded=0'),
                                                  ('empty_frontier', ':', 'frontier=0')]:
                        values = [data.metrics[(graph, algo, t, variant, filt, d)][metric] for d in ds]
                        ax.plot(ds, values, color=color, linestyle=style, label=f'{filt}: {label}')
                ax.set_title(f'{algo}, t={t}, {variant}')
                decorate(ax, 'Mean phase count (symlog; zero retained)')
                ax.set_yscale('symlog', linthresh=1)
                ax.set_ylim(bottom=-0.1)
                ax.legend(fontsize=8, ncol=2)
            fig.suptitle(f'{graph} · Empty phases: expanded == 0 · frontier == 0 shown separately')
            save(fig, f'e1_{graph}_q1_empty_phases')
        fig, ax = plt.subplots(figsize=(12, 5), layout='constrained')
        rules = ['W/d_max', 'W/d_avg'] + [f'overhead_alpha={a:g}' for a in ALPHAS]
        for i, (algo, t, label) in enumerate([('delta-seq', 1, 'seq'), ('delta-omp', 6, 't6'), ('delta-omp', 12, 't12')]):
            subset = {r['rule']: r for r in q4 if (r['graph'], r['algo'], r['threads']) == (graph, algo, t)}
            vals = [subset[r]['slowdown'] if subset[r]['slowdown'] is not None else math.nan for r in rules]
            ax.bar([x + (i - 1) * 0.25 for x in range(len(rules))], vals, width=0.24, label=label, color=COLORS[i])
        ax.axhline(1, color='#444444', linewidth=0.8)
        ax.set_xticks(range(len(rules)), ['W/d_max', 'W/d_avg'] + [f'α={a:g}' for a in ALPHAS])
        ax.set_yscale('log')
        ax.set_ylabel('Slowdown vs fastest measured configuration (log)')
        ax.set_title(f'{graph} · Δ selection rules · fastest variant/filter held fixed per execution mode')
        ax.legend()
        ax.grid(True, axis='y', alpha=0.22)
        save(fig, f'e1_{graph}_q4_slowdown')


def markdown(q4):
    lines = ['# Q4: choosing Δ', '',
             'Times: mean of four source-wise medians of three timing-build repetitions (ms).',
             'The globally fastest variant/filter is held fixed for rule comparisons within each execution mode.',
             'Overhead uses source-matched Dijkstra edges, averaged over four sources; it selects the last passing power-of-two sweep Δ.',
             'The t12 overhead rule uses t6 stats as a proxy; t12 work counters were not measured.', '',
             '| Graph | Mode | Variant/filter | Rule | Δ | Time (ms) | Slowdown |',
             '|---|---|---|---|---:|---:|---:|']
    for r in q4:
        mode = 'seq' if r['algo'] == 'delta-seq' else f't{r["threads"]}'
        ms = f'{r["time_ms"]:.3f}' if r['time_ms'] is not None else 'N/A'
        slow = f'{r["slowdown"]:.3f}×' if r['slowdown'] is not None else 'N/A'
        lines.append(f'| {r["graph"]} | {mode} | {r["variant"]}/{r["filter"]} | {r["rule"]} | '
                     f'{r["delta"] or "N/A"} | {ms} | {slow} |')
    return '\n'.join(lines) + '\n'


def findings_markdown(data, reductions, merge):
    lines = ['# Q1: work, depth and empty phases', '',
             'Primary definition: a logged phase is empty when `expanded == 0`. '
             '`frontier == 0` and `edges == 0` are separate diagnostics in `q1_metrics.csv`.',
             'Counts below are arithmetic means across the four fixed sources. '
             'The attribution compares the smallest to the largest power-of-two sweep Δ.', '',
             '| Graph | Mode | Variant/filter | Δ endpoints | Phases, small → large | '
             'Empty expanded, small → large | Empty share of phase reduction |',
             '|---|---|---|---|---:|---:|---:|']
    for r in reductions:
        if r['comparison'] != 'largest_sweep_delta':
            continue
        mode = 'seq' if r['algo'] == 'delta-seq' else 't6'
        share = f'{100*r["empty_share"]:.2f}%' if r['empty_share'] is not None else 'N/A'
        lines.append(f'| {r["graph"]} | {mode} | {r["variant"]}/{r["filter"]} | '
                     f'{r["small_delta"]} → {r["larger_delta"]} | '
                     f'{r["phases_small"]:.2f} → {r["phases_large"]:.2f} | '
                     f'{r["empty_expanded_small"]:.2f} → {r["empty_expanded_large"]:.2f} | {share} |')
    if not reductions:
        lines += ['', 'Phase reductions are pending; synchronize the compute-side summary cache.']
    lines += ['', 'The residual phase reduction comes from fewer nonempty phases, not fewer empty phases. '
              'See `q1_phase_reduction.csv` for comparisons against each pair’s best Δ as well.', '',
              '## Does Merge move the fastest Δ?', '',
              '| Graph | Mode | Variant | Pop best Δ / ms | Merge best Δ / ms | Δ changed? |',
              '|---|---|---|---:|---:|---|']
    for r in merge:
        mode = 'seq' if r['algo'] == 'delta-seq' else f't{r["threads"]}'
        lines.append(f'| {r["graph"]} | {mode} | {r["variant"]} | '
                     f'{r["pop_best_delta"]} / {r["pop_time_ms"]:.3f} | '
                     f'{r["merge_best_delta"]} / {r["merge_time_ms"]:.3f} | '
                     f'{"yes" if r["best_delta_moved"] else "no"} |')
    lines += ['', '## Coverage', '',
              f'Complete graphs: {", ".join(data.graphs)}. Pending: {", ".join(data.pending) or "none"}.',
              f'Reduced phase runs matched to stats CSVs: {len(data.phases)} / {len(data.stats)}.',
              'Work/depth plots use seq/t6 stats; timing plots also include measured t12 timings. '
              'Each performance point is the mean of four per-source medians of three repetitions.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-plots', action='store_true')
    args = parser.parse_args()
    data = Data()
    q4 = q4_rows(data)
    reductions, merge = phase_findings(data)
    write_csv(OUT / 'q4_table.csv', q4)
    (OUT / 'q4_table.md').write_text(markdown(q4))
    write_csv(OUT / 'q1_phase_reduction.csv', reductions)
    write_csv(OUT / 'q1_merge_best.csv', merge)
    (OUT / 'q1_findings.md').write_text(findings_markdown(data, reductions, merge))
    metrics = []
    for key, values in sorted(data.metrics.items()):
        metrics.append(dict(zip(('graph', 'algo', 'threads', 'variant', 'filter', 'delta'), key), **values))
    # Phase columns are absent until that graph's reduction cache has arrived.
    for row in metrics:
        for name in ('empty_frontier', 'empty_expanded', 'empty_edges'):
            row.setdefault(name, None)
    write_csv(OUT / 'q1_metrics.csv', metrics)
    if not args.no_plots:
        plots(data, q4)
    metadata = dict(graphs=data.graphs, pending=data.pending, input_sha256=data.inputs,
                    manifest_sha256=sha(OUT / 'jobs.json'), analysis_sha256=sha(pathlib.Path(__file__)),
                    local_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    command=['python3', 'analysis/e1_analysis.py'],
                    phase_runs_expected=len(data.stats), phase_runs_reduced=len(data.phases))
    (OUT / 'ANALYSIS_META.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(f'PASS: analyzed complete graphs {data.graphs}; pending {data.pending}')
    print(f'PASS: {len(q4)} Q4 rows, {len(merge)} Pop/Merge optimum comparisons, '
          f'{len(reductions)} empty-phase reduction comparisons')
    print(f'Phase reductions available: {len(data.phases)}/{len(data.stats)} stats runs')
    for row in q4:
        if row['rule'] == 'fastest':
            print(f'BEST {row["graph"]} {row["algo"]} t{row["threads"]} '
                  f'{row["variant"]}/{row["filter"]}: delta={row["delta"]} ms={row["time_ms"]:.4f}')


if __name__ == '__main__':
    main()
