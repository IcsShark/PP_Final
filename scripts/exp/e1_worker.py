#!/usr/bin/env python3
"""Compute-node worker. Only publishes a CSV/.done after full verification."""
import argparse
import csv
import gzip
import json
import os
import signal
import socket
import subprocess
import time
import traceback

from e1_common import DATA, OUT, PHASE_HEADER, RAW, ROOT, digest, job_path, load_manifest, read_rows, revision, validate_rows


def run_checked(cmd, csv_path, log_path):
    with log_path.open('a') as log:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        try:
            deadline = time.monotonic() + 1100
            while proc.poll() is None:
                if time.monotonic() > deadline:
                    raise TimeoutError('kernel invocation exceeded 1100 seconds')
                for row in read_rows(csv_path):
                    if row.get('verified') == '0':
                        raise RuntimeError('verified=0: stopping experiment immediately')
                if 'WRONG' in log_path.read_text(errors='replace') or 'MISMATCH' in log_path.read_text(errors='replace'):
                    raise RuntimeError('WRONG/MISMATCH: stopping experiment immediately')
                time.sleep(0.5)
            if proc.returncode:
                raise RuntimeError(f'kernel exited {proc.returncode}; see {log_path}')
        except BaseException:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise
    validate_rows(read_rows(csv_path))


def worker(job):
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    stem = OUT / job['id']
    final = job_path(job)
    done = stem.with_suffix('.done')
    if done.exists():
        validate_rows(read_rows(final), len(job['sources']) * len(job['deltas']) * job['reps'])
        return
    start = time.time()
    partial = stem.with_suffix('.csv.partial')
    if partial.exists():
        partial.rename(str(partial) + f'.previous.{time.time_ns()}')
    log = stem.with_suffix('.kernel.log')
    host = socket.gethostname()
    hardware = OUT / f'lscpu.{host}.txt'
    if not hardware.exists():
        hardware.write_text(subprocess.check_output(['lscpu'], text=True))
    affinity = sorted(os.sched_getaffinity(0))
    if len(affinity) < 12:
        raise RuntimeError(f'whole-node allocation required, affinity={affinity}')
    is_dij = job['algo'] == 'dijkstra'
    is_stats = 'stats' in job['kind']
    if is_dij:
        source_groups = [None]
    else:
        rows = read_rows(OUT / f'dijkstra_stats_{job["graph"]}.csv')
        validate_rows(rows, 4)
        sources = [int(r['source']) for r in rows]
        source_groups = [sources[i] for i in job['sources']]
    phase_paths = []
    commands = []
    for source in source_groups:
        cmd = [str(ROOT / 'bin' / ('sssp_stats' if is_stats else 'sssp')),
               '-g', str(DATA / (job['graph'] + '.csr')), '-a', job['algo'],
               '-d', ','.join(map(str, job['deltas'])), '-t', str(job['threads']),
               '--variant', job['variant'], '--filter', job['filter'],
               '--seed', '42', '-r', str(job['reps']), '--verify', '--csv', str(partial), '-q']
        cmd += ['--sources', '4'] if source is None else ['--source', str(source)]
        phase = None
        if is_stats and not is_dij:
            phase = RAW / f'{job["id"]}_source{source}.phases.csv.partial'
            if phase.exists():
                phase.rename(str(phase) + f'.previous.{time.time_ns()}')
            cmd += ['--phase-log', str(phase)]
        commands.append(cmd)
        metadata = dict(job=job['id'], commit=revision(), manifest_sha256=digest(OUT / 'jobs.json'),
                        hostname=host, affinity=affinity, command=cmd, time=time.time(),
                        OMP_PROC_BIND=os.getenv('OMP_PROC_BIND', 'unset'),
                        OMP_PLACES=os.getenv('OMP_PLACES', 'unset'), phase_log=str(phase))
        with (OUT / 'META.txt').open('a') as f:
            f.write(json.dumps(metadata) + '\n')
        run_checked(cmd, partial, log)
        if phase:
            with phase.open() as f:
                if next(csv.reader(f)) != PHASE_HEADER:
                    raise RuntimeError(f'wrong phase log header: {phase}')
            compressed = phase.with_suffix('.gz')
            with phase.open('rb') as src, gzip.open(str(compressed) + '.partial', 'wb', compresslevel=1) as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
            os.replace(str(compressed) + '.partial', compressed)
            phase.unlink()
            phase_paths.append(str(compressed))
    rows = read_rows(partial)
    validate_rows(rows, len(job['sources']) * len(job['deltas']) * job['reps'])
    if any(int(r['stats_build']) != int(is_stats) for r in rows):
        raise RuntimeError('wrong executable build')
    os.replace(partial, final)
    reducer = ROOT / 'analysis/e1_phase_reduce.py'
    reduction_timeout = min(150, 1160 - (time.time() - start))
    if reducer.exists() and reduction_timeout >= 5:
        reduction_cmd = ['python3', str(reducer), '--files', *phase_paths,
                         '--backlog-graphs', 'NY', 'LJ', job['graph'],
                         '--budget-seconds', str(min(90, reduction_timeout)), '--max-files', '24']
        with (OUT / 'META.txt').open('a') as f:
            f.write(json.dumps(dict(analysis_command=reduction_cmd, hostname=host,
                                    timing_note='post-kernel reduction; excluded from CSV kernel timings')) + '\n')
        try:
            with (OUT / 'phase_reduction.log').open('a') as reduction_log:
                result = subprocess.run(reduction_cmd, stdout=reduction_log, stderr=subprocess.STDOUT,
                                        timeout=reduction_timeout)
            if result.returncode:
                (OUT / 'phase_reduction.failed').write_text(f'{job["id"]}: reducer exited {result.returncode}\n')
        except subprocess.TimeoutExpired:
            (OUT / 'phase_reduction.failed').write_text(
                f'{job["id"]}: reducer exceeded {reduction_timeout:.1f}s; cache is resumable\n')
    record = dict(job=job['id'], seconds=time.time() - start, hostname=host, rows=len(rows),
                  csv_sha256=digest(final), manifest_sha256=digest(OUT / 'jobs.json'),
                  phase_logs=phase_paths, commands=commands)
    done.with_suffix('.done.tmp').write_text(json.dumps(record, indent=2) + '\n')
    os.replace(done.with_suffix('.done.tmp'), done)
    print(f'{job["id"]}: verified {len(rows)} rows in {record["seconds"]:.2f}s', flush=True)


def main():
    def interrupted(signum, frame):
        raise TimeoutError(f'worker interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser()
    parser.add_argument('job')
    args = parser.parse_args()
    job = next(j for j in load_manifest()['jobs'] if j['id'] == args.job)
    try:
        worker(job)
    except BaseException:
        failure = traceback.format_exc()
        (OUT / (job['id'] + '.failed')).write_text(failure)
        (OUT / 'STOPPED').write_text(failure)
        raise


if __name__ == '__main__':
    main()
