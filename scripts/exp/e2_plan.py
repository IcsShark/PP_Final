#!/usr/bin/env python3
"""Freeze E2 choices only after a graph's complete, verified E1 grid lands."""
import collections
import json
import statistics

from e1_common import OUT as E1, ROOT, digest, read_rows, validate_rows

OUT = ROOT / 'results/e2_scaling'
THREADS = (1, 2, 4, 6, 8, 12)


def neighbours(best, sweep):
    lower = [d for d in sweep if d < best]
    upper = [d for d in sweep if d > best]
    return sorted(set([best] + lower[-1:] + upper[:1]))


def prepare(graph, manifest):
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / (graph + '.json')
    if target.exists():
        return json.loads(target.read_text())
    jobs = [j for j in manifest['jobs'] if j['graph'] == graph]
    if not jobs or not all((E1 / (j['id'] + '.done')).exists() for j in jobs):
        return None
    values, hashes = collections.defaultdict(list), {}
    for job in jobs:
        path = E1 / (job['id'] + '.csv')
        marker = json.loads(path.with_suffix('.done').read_text())
        if marker['csv_sha256'] != digest(path):
            raise ValueError(f'E1 digest mismatch: {path}')
        rows = read_rows(path)
        validate_rows(rows, len(job['sources']) * len(job['deltas']) * job['reps'])
        hashes[path.name] = digest(path)
        if job['kind'] == 'timing' and job['algo'] == 'delta-omp':
            for r in rows:
                if r['stats_build'] != '0':
                    raise ValueError('stats timings cannot select E2 settings')
                values[(r['variant'], r['filter'], int(r['threads']), int(r['delta']), int(r['source']))].append(float(r['time_ms']))
    grouped = collections.defaultdict(list)
    for key, times in values.items():
        if len(times) != 3:
            raise ValueError('expected three E1 timing repetitions')
        grouped[key[:-1]].append(statistics.median(times))
    if any(len(v) != 4 for v in grouped.values()):
        raise ValueError('expected four E1 sources')
    times = {k: statistics.mean(v) for k, v in grouped.items()}
    pair = min(times, key=lambda k: (times[k], k))[:2]
    anchors = {str(t): min((d for v, f, th, d in times if (v, f) == pair and th == t),
                           key=lambda d: times[(*pair, t, d)]) for t in (6, 12)}
    sweep = manifest['profiles'][graph]['sweep']
    deltas = sorted({d for anchor in anchors.values() for d in neighbours(anchor, sweep)})
    result = dict(graph=graph, variant=pair[0], filter=pair[1], anchors=anchors, deltas=deltas,
                  e1_sha256=hashes, selection='global fastest E1 OMP pair; pair held fixed for t6/t12 anchors', jobs=[])
    for kind, reps in (('timing', 3), ('stats', 1)):
        for t in THREADS:
            for block, start in enumerate(range(0, len(deltas), 2)):
                result['jobs'].append(dict(id=f'{kind}_{graph}_{pair[0]}_{pair[1]}_t{t}_b{block}', graph=graph,
                    kind=kind, algo='delta-omp', variant=pair[0], filter=pair[1], threads=t,
                    deltas=deltas[start:start+2], reps=reps, sources=[0, 1, 2, 3]))
    temporary = target.with_suffix('.json.partial')
    temporary.write_text(json.dumps(result, indent=2) + '\n')
    temporary.replace(target)
    return result
