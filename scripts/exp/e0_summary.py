#!/usr/bin/env python3
import csv
import json
import pathlib
import statistics
import math

root = pathlib.Path(__file__).resolve().parents[2]
out = root / 'results/e0_calibration'
note = ('Observed lscpu: KVM guest, 12 cores x 1 thread per core; SMT placement cannot be '
        'controlled from guest topology. All final calibration timings allocate run -c 12.\n'
        'Build: module load pp && run -c 4 -- timeout 1200 make -j4\n'
        'Tests/profiles: module load pp && run -c 6 -- timeout 1200 bash scripts/exp/e0_calibrate.sh setup\n')
meta = out / 'META.txt'
if note not in meta.read_text():
    with meta.open('a') as f:
        f.write(note)
with (root / 'results/profile/META.txt').open('w') as f:
    f.write('commit=' + (out / 'COMMIT.txt').read_text())
    f.write('hostname=' + (out / 'hostname.txt').read_text())
    f.write('module load pp && run -c 6 -- timeout 1200 bash scripts/exp/e0_calibrate.sh setup\n')
    for graph in ('NY', 'CTR', 'USA', 'LJ', 'OK', 'kron23', 'urand23', 'grid2896'):
        f.write(f'bin/profile /u/cs/111/111550055/pp_data/csr/{graph}.csr > results/profile/{graph}.json\n')
rows = []
for path in sorted(out.glob('*.csv')):
    if not path.with_suffix('.done').exists():
        continue
    data = list(csv.DictReader(path.open()))
    if len(data) != 3 or any(r['verified'] != '1' for r in data):
        raise RuntimeError(f'incomplete or unverified: {path}')
    row = data[0].copy()
    row['time_ms'] = f"{statistics.median(float(r['time_ms']) for r in data):.4f}"
    row['file'] = path.name
    rows.append(row)
with (out / 'medians.tsv').open('w') as f:
    keys = ['graph', 'algo', 'delta', 'threads', 'source', 'time_ms', 'phases', 'file']
    writer = csv.DictWriter(f, keys, delimiter='\t', extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
print((out / 'medians.tsv').read_text())
print('PROFILE: graph n m d_avg d_max w_min w_max rule_dmax rule_davg sweep_length')
for graph in ('NY', 'CTR', 'USA', 'LJ', 'OK', 'kron23', 'urand23', 'grid2896'):
    p = json.loads((root / 'results/profile' / (graph + '.json')).read_text())
    print(graph, *(p[k] for k in ('n', 'm', 'd_avg', 'd_max', 'w_min', 'w_max',
                                'delta_rule_dmax', 'delta_rule_davg')), len(p['delta_sweep']))
print('E1 provisional planning: graph modeled_minutes budget_minutes jobs_at_20min')
for graph in ('NY', 'CTR', 'USA', 'LJ', 'OK', 'kron23', 'urand23', 'grid2896'):
    rr = [r for r in rows if r['graph'] == graph and '_allocation' not in r['file']]
    points = {}
    for t in (1, 12):
        points[t] = sorted((int(r['delta']), float(r['time_ms'])) for r in rr
                           if r['algo'] == 'delta-omp' and int(r['threads']) == t)
    if any(len(v) != 3 for v in points.values()):
        continue
    seqmid = next(float(r['time_ms']) for r in rr if r['algo'] == 'delta-seq')
    ratio = seqmid / points[1][1][1]
    t6 = [float(r['time_ms']) for r in rr if r['algo'] == 'delta-omp' and r['threads'] == '6']
    ratio6 = t6[0] / points[12][1][1] if t6 else 1.0
    def estimate(t, d):
        ps = points[t]
        for (a, x), (b, y) in zip(ps, ps[1:]):
            if a <= d <= b:
                f = math.log(d / a) / math.log(b / a)
                return math.exp(math.log(x) * (1 - f) + math.log(y) * f)
        raise ValueError(d)
    p = json.loads((root / 'results/profile' / (graph + '.json')).read_text())
    # Four variant/filter combinations, four sources; stats budgeted at 2x timing.
    # t=6 inferred from t=12 where no t=6 calibration exists; no warmup assumed.
    ms = 16 * sum(5 * ratio * estimate(1, d) + (5 * ratio6 + 3) * estimate(12, d)
                  for d in p['delta_sweep'])
    modeled = ms / 60000
    budget = max(2, 2 * modeled)
    print(graph, round(modeled, 2), round(budget, 2), math.ceil(budget / 20))
