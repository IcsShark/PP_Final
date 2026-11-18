#!/usr/bin/env python3
"""Verified whole-node E2 worker; phase reduction never runs on the login node."""
import argparse
import gzip
import json
import os
import pathlib
import signal
import socket
import sys
import time
import traceback

from e1_common import DATA, OUT as E1, ROOT, digest, read_rows, revision, validate_rows
from e1_worker import run_checked
from e2_plan import OUT

sys.path.insert(0, str(ROOT / 'analysis'))
from e2_phase_reduce import summarize

RAW = pathlib.Path.home() / 'devin/results_raw/e2'


def worker(job):
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    if len(os.sched_getaffinity(0)) < 12:
        raise RuntimeError('E2 requires whole-node -c 12 allocation')
    start = time.time()
    final = OUT / (job['id'] + '.csv')
    partial = final.with_suffix('.csv.partial')
    if partial.exists():
        partial.rename(str(partial) + f'.previous.{time.time_ns()}')
    sources = [r['source'] for r in read_rows(E1 / f'dijkstra_stats_{job["graph"]}.csv')]
    if len(sources) != 4 or len(set(sources)) != 4:
        raise ValueError('missing E1 source baseline')
    summaries, paths, commands = [], [], []
    stats = job['kind'] == 'stats'
    for source in sources:
        phase = RAW / f'{job["id"]}_source{source}.phases.csv.partial'
        cmd = [str(ROOT / 'bin' / ('sssp_stats' if stats else 'sssp')), '-g', str(DATA / (job['graph'] + '.csr')),
               '-a', 'delta-omp', '-t', str(job['threads']), '-d', ','.join(map(str, job['deltas'])),
               '--variant', job['variant'], '--filter', job['filter'], '--source', source,
               '--seed', '42', '-r', str(job['reps']), '--verify', '--csv', str(partial), '-q']
        if stats:
            if phase.exists():
                phase.rename(str(phase) + f'.previous.{time.time_ns()}')
            cmd += ['--phase-log', str(phase)]
        commands.append(cmd)
        with (OUT / 'META.txt').open('a') as f:
            f.write(json.dumps(dict(job=job['id'], command=cmd, hostname=socket.gethostname(),
                commit=revision(), allocation=12, affinity=sorted(os.sched_getaffinity(0)),
                topology_note='E0 guest lscpu: 12 cores x 1 thread; not assumed 6 physical cores')) + '\n')
        run_checked(cmd, partial, OUT / (job['id'] + '.kernel.log'))
        if stats:
            with phase.open() as f:
                summaries.extend(summarize(f))
            compressed = phase.with_suffix('.gz')
            with phase.open('rb') as src, gzip.open(str(compressed) + '.partial', 'wb', compresslevel=1) as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
            os.replace(str(compressed) + '.partial', compressed)
            phase.unlink()
            paths.append(str(compressed))
        if time.time() - start > 1100:
            raise TimeoutError('E2 block exceeded 1100s; split before retrying')
    rows = read_rows(partial)
    validate_rows(rows, 4 * len(job['deltas']) * job['reps'])
    if any(int(r['stats_build']) != int(stats) for r in rows):
        raise ValueError('wrong build')
    for r in summaries:
        match = next(x for x in rows if x['source'] == r['source'] and x['delta'] == r['delta'])
        if int(match['phases']) != r['phases'] or int(match['edges_scanned']) != r['edges']:
            raise ValueError('phase summary disagrees with stats CSV')
    final_summary = OUT / (job['id'] + '.phases.json')
    if stats:
        temporary = final_summary.with_suffix('.json.partial')
        temporary.write_text(json.dumps(summaries, indent=2) + '\n')
        temporary.replace(final_summary)
    partial.replace(final)
    record = dict(seconds=time.time()-start, csv_sha256=digest(final), phase_logs=paths,
                  summary_sha256=digest(final_summary) if stats else None, commands=commands,
                  plan_sha256=digest(OUT / (job['graph'] + '.json')), hostname=socket.gethostname())
    temporary = final.with_suffix('.done.partial')
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    temporary.replace(final.with_suffix('.done'))
    print(f'DONE {job["id"]}: {len(rows)} verified rows in {record["seconds"]:.1f}s', flush=True)


def main():
    def interrupted(signum, frame):
        raise TimeoutError(f'E2 interrupted: {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser()
    parser.add_argument('graph')
    parser.add_argument('job')
    args = parser.parse_args()
    job = next(j for j in json.loads((OUT / (args.graph + '.json')).read_text())['jobs'] if j['id'] == args.job)
    try:
        worker(job)
    except BaseException:
        failure = traceback.format_exc()
        (OUT / (job['id'] + '.failed')).write_text(failure)
        (OUT / 'STOPPED').write_text(failure)
        raise


if __name__ == '__main__':
    main()
