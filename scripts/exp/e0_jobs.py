#!/usr/bin/env python3
import json
import pathlib
import shlex
import subprocess
import time

root = pathlib.Path(__file__).resolve().parents[2]
with (root / 'results/e0_calibration/META.txt').open('a') as meta:
    meta.write('Owner decision: all subsequent timing and stats runs allocate run -c 12 (whole node). '
               'NY delta=256 t=6: c6=21.0163 ms, c12=19.9174 ms; '
               'CTR delta=512 t=6: c6=590.5063 ms, c12=509.2803 ms. '
               'Earlier smaller allocations retained under superseded_allocation; '
               'oversubscribed runs retained under invalid_allocation.\n')
for graph in ('NY', 'CTR', 'USA', 'LJ', 'OK', 'kron23', 'urand23', 'grid2896'):
    profile = json.loads((root / 'results/profile' / (graph + '.json')).read_text())
    sweep = profile['delta_sweep']
    deltas = list(dict.fromkeys((sweep[0], sweep[len(sweep) // 2], sweep[-1])))
    configs = [('dijkstra', 1, 1), ('delta-seq', deltas[1], 1)]
    configs += [('delta-omp', d, t) for d in deltas for t in (1, 12)]
    if graph in ('NY', 'CTR'):
        configs += [('delta-omp', deltas[1], 6)]
    commands = []
    stems = []
    out = root / 'results/e0_calibration'
    for algo, delta, threads in configs:
        stem = f'{graph}_{algo}_{delta}_{threads}'
        if (out / (stem + '.done')).exists():
            continue
        commands.append(shlex.join(['bash', 'scripts/exp/e0_calibrate.sh', 'config',
                                    graph, algo, str(delta), str(threads)]) +
                        ' > ' + shlex.quote(str(out / (stem + '.log'))) + ' 2>&1')
        stems.append(stem)
    if not commands:
        continue
    cmd = ['run', '-c', '12', '--', 'timeout', '1200', 'bash', '-c', ' && '.join(commands)]
    with (out / 'META.txt').open('a') as meta:
        meta.write(shlex.join(cmd) + '\n')
    print(shlex.join(cmd), flush=True)
    subprocess.run(cmd, cwd=root, check=True)
    for stem in stems:
        for _ in range(30):
            if (out / (stem + '.done')).exists():
                break
            time.sleep(2)
        if not (out / (stem + '.done')).exists():
            raise RuntimeError(f'{stem} failed: run wrapper does not propagate compute exit status; see log')
print('E0 calibration complete', flush=True)
