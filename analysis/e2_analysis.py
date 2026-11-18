#!/usr/bin/env python3
"""Q2/Q3 analysis of complete E2 graphs; stats times are never performance data."""
import collections
import json
import pathlib
import statistics
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from e1_analysis import Data, ROOT, PLOTS, sha, write_csv

sys.path.insert(0, str(ROOT / 'scripts/exp'))
from e1_common import read_rows, validate_rows
from e2_plan import OUT, THREADS


def source_medians(rows):
    grouped = collections.defaultdict(list)
    for r in rows:
        grouped[int(r['source'])].append(float(r['time_ms']))
    if len(grouped) != 4 or any(len(v) != 3 for v in grouped.values()):
        raise ValueError('expected four sources x three timing repetitions')
    return statistics.mean(statistics.median(v) for v in grouped.values())


def load():
    e1 = Data()
    output, hashes = [], {}
    pending = set(e1.manifest['profiles'])
    for path in sorted(OUT.glob('*.json')):
        if path.stem not in e1.manifest['profiles']:
            continue
        plan = json.loads(path.read_text())
        graph = plan['graph']
        if not all((OUT / (j['id'] + '.done')).exists() for j in plan['jobs']):
            continue
        pending.discard(graph)
        hashes[str(path.relative_to(ROOT))] = sha(path)
        for name, expected in plan['e1_sha256'].items():
            if sha(e1.out / name) != expected:
                raise ValueError('E1 selection input changed')
        timing, stats, summaries = collections.defaultdict(list), {}, {}
        for job in plan['jobs']:
            csv_path = OUT / (job['id'] + '.csv')
            marker = json.loads(csv_path.with_suffix('.done').read_text())
            if sha(csv_path) != marker['csv_sha256'] or sha(path) != marker['plan_sha256']:
                raise ValueError('E2 CSV or selection digest mismatch')
            hashes[str(csv_path.relative_to(ROOT))] = sha(csv_path)
            rows = read_rows(csv_path)
            validate_rows(rows, 4 * len(job['deltas']) * job['reps'])
            for r in rows:
                if int(r['stats_build']) != int(job['kind'] == 'stats'):
                    raise ValueError('wrong build in E2 CSV')
                key = (int(r['threads']), int(r['delta']))
                if job['kind'] == 'timing':
                    timing[key].append(r)
                else:
                    full = (*key, int(r['source']))
                    if full in stats:
                        raise ValueError('duplicate E2 stats run')
                    stats[full] = r
            if job['kind'] == 'stats':
                reduced = OUT / (job['id'] + '.phases.json')
                if sha(reduced) != marker['summary_sha256']:
                    raise ValueError('E2 summary digest mismatch')
                hashes[str(reduced.relative_to(ROOT))] = sha(reduced)
                for r in json.loads(reduced.read_text()):
                    key = (int(r['threads']), int(r['delta']), int(r['source']))
                    if key in summaries:
                        raise ValueError('duplicate reduced E2 phase run')
                    summaries[key] = r
        times = {k: source_medians(v) for k, v in timing.items()}
        seq_ms, seq_key = e1.best(graph, 'delta-seq', 1)
        dij_path = e1.out / f'dijkstra_timing_{graph}.csv'
        dij_rows = read_rows(dij_path)
        validate_rows(dij_rows, 12)
        if any(r['stats_build'] != '0' for r in dij_rows):
            raise ValueError('Dijkstra baseline must be timing build')
        dij_ms = source_medians(dij_rows)
        sources = sorted({int(r['source']) for r in dij_rows})
        for t in THREADS:
            for d in plan['deltas']:
                time_ms = times[t, d]
                counters, ideals, free = [], [], []
                for source in sources:
                    r, p = stats[t, d, source], summaries[t, d, source]
                    if int(r['phases']) != p['phases'] or int(r['edges_scanned']) != p['edges']:
                        raise ValueError('phase summary disagrees with CSV')
                    if p['phases'] <= 0 or p['ideal'][str(t)] <= 0 or p['ideal_no_max'][str(t)] <= 0:
                        raise ValueError('zero ideal cost or phase denominator')
                    counters.append((p['phases'], p['edges'] / p['phases']))
                    ideals.append(p['edges'] / p['ideal'][str(t)])
                    free.append(p['edges'] / p['ideal_no_max'][str(t)])
                output.append(dict(graph=graph, variant=plan['variant'], filter=plan['filter'], threads=t, delta=d,
                    time_ms=time_ms, seq_time_ms=seq_ms, seq_delta=seq_key[-1], dijkstra_time_ms=dij_ms,
                    speedup_seq=seq_ms/time_ms, speedup_dijkstra=dij_ms/time_ms,
                    speedup_omp1=times[1, d]/time_ms, efficiency_seq=seq_ms/time_ms/t,
                    efficiency_omp1=times[1, d]/time_ms/t, phases=statistics.mean(v[0] for v in counters),
                    average_parallelism=statistics.mean(v[1] for v in counters),
                    ideal_speedup=statistics.mean(ideals), ideal_no_max_speedup=statistics.mean(free)))
    if not output:
        raise ValueError('no complete E2 graphs; synchronize plans, CSVs, .done and .phases.json first')
    return output, hashes, [g for g in e1.manifest['profiles'] if g in pending]


def best_rows(rows):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r['graph'], r['threads']].append(r)
    return [min(v, key=lambda r: (r['time_ms'], r['delta'])) for v in groups.values()]


def markdown(rows):
    lines = ['# E2 thread scaling', '',
        'Timing: mean of four source-wise medians of three normal-build repetitions. '
        'Each row chooses the fastest measured Δ at that thread count from the frozen E2 candidate set.',
        'Efficiency below = speedup vs best E1 delta-seq / threads. CSVs also provide OMP-t1 efficiency.',
        'Ideal speedups average source-matched T1/Tk on each row’s own measured phase decomposition; '
        'T1=sum(edges). The measured-vs-ideal figures use OMP-t1 at the SAME Δ as their measured baseline.',
        'E0 guest topology was 12 cores × 1 thread; a six-physical-core knee is a hypothesis, not assumed hardware.', '',
        '| Graph | t | Δ | ms | vs seq | vs Dijkstra | Efficiency | Ideal max | Ideal no-max | Phases | Edges/phase |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f'| {r["graph"]} | {r["threads"]} | {r["delta"]} | {r["time_ms"]:.3f} | '
            f'{r["speedup_seq"]:.3f} | {r["speedup_dijkstra"]:.3f} | {100*r["efficiency_seq"]:.1f}% | '
            f'{r["ideal_speedup"]:.3f} | {r["ideal_no_max_speedup"]:.3f} | {r["phases"]:.1f} | '
            f'{r["average_parallelism"]:.1f} |')
    return '\n'.join(lines) + '\n'


def save(fig, name):
    fig.savefig(PLOTS / (name + '.png'), dpi=160, bbox_inches='tight')
    fig.savefig(PLOTS / (name + '.pdf'), bbox_inches='tight')
    plt.close(fig)


def plots(rows, best):
    PLOTS.mkdir(parents=True, exist_ok=True)
    graphs = sorted({r['graph'] for r in rows})
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), layout='constrained')
    panels = [('speedup_seq', 'Speedup / best E1 delta-seq'), ('speedup_dijkstra', 'Speedup / E1 Dijkstra'),
              ('efficiency_seq', 'Efficiency vs seq (speedup / threads)'), ('phases', 'Mean phases'),
              ('average_parallelism', 'Mean source edges scanned / phases'), ('speedup_omp1', 'Speedup / OMP t1 at selected Δ')]
    for ax, (key, label) in zip(axes.flat, panels):
        for graph in graphs:
            rr = sorted((r for r in best if r['graph'] == graph), key=lambda r: r['threads'])
            ax.plot([r['threads'] for r in rr], [r[key] for r in rr], marker='o', label=graph)
        ax.set_xticks(THREADS)
        ax.set_xlabel('Threads (whole-node allocation)')
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.2)
        if key in ('phases', 'average_parallelism'):
            ax.set_yscale('log')
    axes[0, 0].legend()
    fig.suptitle('E2 · Q2 topology comparison · fastest candidate Δ per thread count')
    save(fig, 'e2_q2_scaling')
    for graph in graphs:
        deltas = sorted({r['delta'] for r in rows if r['graph'] == graph})
        cols = min(3, len(deltas))
        nrows = (len(deltas) + cols - 1) // cols
        fig, axes = plt.subplots(nrows, cols, figsize=(5*cols, 4.5*nrows), squeeze=False, layout='constrained')
        for ax in list(axes.flat)[len(deltas):]:
            ax.set_visible(False)
        for ax, delta in zip(axes.flat, deltas):
            rr = sorted((r for r in rows if r['graph'] == graph and r['delta'] == delta), key=lambda r: r['threads'])
            for key, label, style in [('speedup_omp1', 'Measured / OMP t1', '-o'),
                                      ('ideal_speedup', 'Ideal: vertex maximum', '--s'),
                                      ('ideal_no_max_speedup', 'Ideal: no maximum', ':^')]:
                ax.plot([r['threads'] for r in rr], [r[key] for r in rr], style, label=label)
            ax.set_title(f'Δ={delta}')
            ax.set_xlabel('Threads')
            ax.set_ylabel('Speedup')
            ax.set_xticks(THREADS)
            ax.grid(True, alpha=0.2)
            ax.legend(fontsize=8)
        fig.suptitle(f'{graph} · Q3 measured vs phase-log ideals · fixed Δ per panel')
        save(fig, f'e2_{graph}_q3_ideal')


def main():
    rows, hashes, pending = load()
    best = best_rows(rows)
    write_csv(OUT / 'all_runs.csv', rows)
    write_csv(OUT / 'scaling_table.csv', best)
    report = markdown(best)
    (OUT / 'scaling_table.md').write_text(report)
    plots(rows, best)
    (OUT / 'ANALYSIS_META.json').write_text(json.dumps(dict(input_sha256=hashes,
        analysis_sha256=sha(pathlib.Path(__file__)), pending=pending), indent=2) + '\n')
    print(f'PASS: {len(rows)} E2 Δ/thread points; {len(best)} scaling rows; pending {pending}')
    print(report)


if __name__ == '__main__':
    main()
