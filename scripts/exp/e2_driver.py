#!/usr/bin/env python3
"""Single-lock E1/E2 queue: E2 becomes eligible after each complete E1 graph."""
import fcntl
import json
import os
import shlex
import subprocess
import time

from e1_common import ORDER, OUT as E1, ROOT, digest, load_manifest, read_rows, validate_rows
from e2_plan import OUT as E2, prepare


def complete(job, out):
    path = out / (job['id'] + '.csv')
    marker = path.with_suffix('.done')
    if not marker.exists():
        return False
    record = json.loads(marker.read_text())
    if digest(path) != record['csv_sha256']:
        raise ValueError(f'completed CSV changed: {path}')
    validate_rows(read_rows(path), len(job['sources']) * len(job['deltas']) * job['reps'])
    if out == E1 and record.get('phase_summary'):
        if digest(E1 / 'phase_summaries' / os.path.basename(record['phase_summary'])) != record['phase_summary_sha256']:
            raise ValueError('E1 phase summary changed')
    if job['kind'] == 'stats' and out == E2:
        if digest(out / (job['id'] + '.phases.json')) != record['summary_sha256']:
            raise ValueError('E2 phase summary changed')
    if out == E2 and digest(out / (job['graph'] + '.json')) != record['plan_sha256']:
        raise ValueError('E2 selection changed')
    return True


def choose(manifest):
    for graph in ORDER:
        plan = prepare(graph, manifest)
        if plan:
            for job in plan['jobs']:
                if not complete(job, E2):
                    return job, E2
    for job in manifest['jobs']:
        if not complete(job, E1):
            return job, E1
    return None


def main():
    E2.mkdir(parents=True, exist_ok=True)
    lock = (E1 / 'driver.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lock.seek(0)
    lock.truncate()
    lock.write(str(os.getpid()) + '\n')
    lock.flush()
    manifest = load_manifest()
    print(f'E1/E2 DRIVER READY pid={os.getpid()}; whole node -c 12; one shared lock', flush=True)
    while True:
        if any((out / 'STOPPED').exists() for out in (E1, E2)):
            raise RuntimeError('STOPPED flag present; inspect before resuming')
        if (E1 / 'PAUSE_AFTER_JOB').exists():
            print('PAUSED BETWEEN JOBS', flush=True)
            return
        selected = choose(manifest)
        if selected is None:
            print('E1 AND E2 COMPLETE', flush=True)
            return
        job, out = selected
        active = subprocess.check_output(['squeue', '-h', '-u', os.environ['USER']], text=True).strip()
        if active:
            raise RuntimeError(f'account already has a job; refusing second submission: {active}')
        args = ['scripts/exp/e2_worker.py', job['graph'], job['id']] if out == E2 else ['scripts/exp/e1_worker.py', job['id']]
        cmd = ['run', '-c', '12', '--', 'timeout', '1190', 'python3', *args]
        with (out / 'META.txt').open('a') as f:
            f.write(shlex.join(cmd) + '\n')
        print(time.strftime('%FT%T%z'), shlex.join(cmd), flush=True)
        start = time.time()
        with (out / (job['id'] + '.run.log')).open('a') as log:
            result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(30):
            if (out / (job['id'] + '.done')).exists() or (out / (job['id'] + '.failed')).exists():
                break
            time.sleep(2)
        if result.returncode or not complete(job, out):
            (out / 'STOPPED').write_text(f'{job["id"]} failed; inspect logs before resuming\n')
            raise RuntimeError(f'{job["id"]} failed')
        print(f'DONE {job["id"]} wall={time.time()-start:.1f}s', flush=True)
        for _ in range(30):
            if not subprocess.check_output(['squeue', '-h', '-u', os.environ['USER']], text=True).strip():
                break
            time.sleep(2)


if __name__ == '__main__':
    try:
        main()
    except BlockingIOError:
        raise
    except Exception as error:
        E2.mkdir(parents=True, exist_ok=True)
        (E2 / 'STOPPED').write_text(str(error) + '\n')
        raise
