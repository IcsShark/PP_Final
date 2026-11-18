#!/usr/bin/env python3
"""Build an immutable E1 manifest from E0 profiles and whole-node calibration."""
import csv
import json
import math

from e1_common import ORDER, OUT, ROOT, revision


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'jobs.json').exists():
        raise SystemExit('jobs.json already exists; resume it rather than overwriting')
    with (ROOT / 'results/e0_calibration/medians.tsv').open() as f:
        calibration = list(csv.DictReader(f, delimiter='\t'))
    jobs = []
    profiles = {}
    for graph in ORDER:
        p = json.loads((ROOT / 'results/profile' / (graph + '.json')).read_text())
        rules = [p['w_max'] / p['d_max'], p['w_max'] * p['n'] / p['m']]
        ds = sorted(set(p['delta_sweep'] + [max(1, math.floor(x + 0.5)) for x in rules]))
        profiles[graph] = {'deltas': ds, 'sweep': p['delta_sweep']}
        rr = [r for r in calibration if r['graph'] == graph and '_allocation' not in r['file']]
        dij = next(float(r['time_ms']) / 1000 for r in rr if r['algo'] == 'dijkstra')
        pts = {t: sorted((int(r['delta']), float(r['time_ms']) / 1000) for r in rr
                         if r['algo'] == 'delta-omp' and int(r['threads']) == t) for t in (1, 12)}
        seq = next(float(r['time_ms']) / 1000 for r in rr if r['algo'] == 'delta-seq')
        def estimate(t, d):
            for (a, x), (b, y) in zip(pts[t], pts[t][1:]):
                if a <= d <= b:
                    q = math.log(d / a) / math.log(b / a)
                    return math.exp(math.log(x) * (1 - q) + math.log(y) * q)
            raise ValueError(d)
        for kind, reps in (('dijkstra_stats', 1), ('dijkstra_timing', 3)):
            jobs.append(dict(id=f'{kind}_{graph}', graph=graph, algo='dijkstra', kind=kind,
                             variant='all', filter='pop', threads=1, sources=[0, 1, 2, 3],
                             deltas=[1], reps=reps, estimate_seconds=4 * (reps + 1) * dij + 20))
        for variant in ('all', 'lh'):
            for filt in ('pop', 'merge'):
                for kind, algo, t, reps in (('timing', 'delta-seq', 1, 3),
                                             ('timing', 'delta-omp', 6, 3),
                                             ('timing', 'delta-omp', 12, 3),
                                             ('stats', 'delta-seq', 1, 1),
                                             ('stats', 'delta-omp', 6, 1)):
                    def cost(d):
                        seconds = estimate(1 if t == 1 else 12, d)
                        if algo == 'delta-seq':
                            seconds *= seq / pts[1][1][1]
                        if t == 6:
                            seconds *= 1.3
                        # Allow stats/logging and uncalibrated variants room to grow.
                        return 2 * (reps * seconds * (2 if kind == 'stats' else 1) + dij + 1)
                    blocks = []
                    block = []
                    for d in ds:
                        if block and 4 * sum(cost(x) for x in block + [d]) > 600:
                            blocks.append(block)
                            block = []
                        block.append(d)
                    if block:
                        blocks.append(block)
                    for bi, block in enumerate(blocks):
                        per_source = sum(cost(d) for d in block)
                        ns = max(1, min(4, int(600 / per_source)))
                        for start in range(0, 4, ns):
                            sources = list(range(start, min(4, start + ns)))
                            ident = f'{kind}_{graph}_{algo}_{variant}_{filt}_t{t}_b{bi:02d}_s{start}'
                            jobs.append(dict(id=ident, graph=graph, algo=algo, kind=kind,
                                             variant=variant, filter=filt, threads=t, sources=sources,
                                             deltas=block, reps=reps,
                                             estimate_seconds=20 + len(sources) * per_source))
    manifest = dict(version=1, source_commit=revision(), allocation=12, seed=42,
                    rounded_rule='floor(value + 0.5), clamped >=1', profiles=profiles, jobs=jobs)
    (OUT / 'jobs.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Created {len(jobs)} serial jobs; predicted {sum(j["estimate_seconds"] for j in jobs)/3600:.2f} h')
    for graph in ORDER:
        js = [j for j in jobs if j['graph'] == graph]
        print(graph, len(js), 'jobs', round(sum(j['estimate_seconds'] for j in js) / 60, 1), 'estimated minutes')


if __name__ == '__main__':
    main()
