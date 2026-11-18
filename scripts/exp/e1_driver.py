#!/usr/bin/env python3
"""Login-node serial launcher: module load pp; nohup python3 scripts/exp/e1_driver.py."""
import fcntl
import json
import os
import shlex
import subprocess
import time

from e1_common import OUT, RAW, ROOT, digest, job_path, load_manifest, read_rows, revision, validate_rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / 'driver.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lock.write(str(os.getpid()) + '\n')
    lock.flush()
    manifest = load_manifest()
    with (OUT / 'META.txt').open('a') as f:
        f.write('E1: all timing/stats jobs run -c 12 (whole node). Guest lscpu reports 12 cores x '
                '1 thread; SMT placement is not controllable. E0 t6 NY c6/c12=21.0163/19.9174 ms; '
                'CTR=590.5063/509.2803 ms. Default schedule dynamic,64 unchanged. '
                f'Phase logs: {RAW}/ (gzip, excluded from commits). '
                f'Commit={revision()} manifest_sha256={digest(OUT / "jobs.json")}\n')
    for job in manifest['jobs']:
        if (OUT / 'STOPPED').exists():
            raise RuntimeError('STOPPED flag present; inspect before resuming')
        done = OUT / (job['id'] + '.done')
        expected = len(job['sources']) * len(job['deltas']) * job['reps']
        if done.exists():
            validate_rows(read_rows(job_path(job)), expected)
            continue
        active = subprocess.check_output(['squeue', '-h', '-u', os.environ['USER']], text=True).strip()
        if active:
            raise RuntimeError(f'account already has a job; refusing to queue another:\n{active}')
        cmd = ['run', '-c', '12', '--', 'timeout', '1190', 'python3',
               'scripts/exp/e1_worker.py', job['id']]
        with (OUT / 'META.txt').open('a') as f:
            f.write(shlex.join(cmd) + '\n')
        print(time.strftime('%FT%T%z'), shlex.join(cmd), flush=True)
        start = time.time()
        with (OUT / (job['id'] + '.run.log')).open('a') as log:
            proc = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        # The wrapper hides compute exit status; NFS markers can become visible late.
        for _ in range(30):
            if done.exists() or (OUT / (job['id'] + '.failed')).exists():
                break
            time.sleep(2)
        if proc.returncode or not done.exists():
            (OUT / 'STOPPED').write_text(f'{job["id"]} failed or exceeded 1190s; inspect .run.log and .failed\n')
            raise RuntimeError(f'{job["id"]} failed; stopping serial driver')
        rows = read_rows(job_path(job))
        validate_rows(rows, expected)
        record = json.loads(done.read_text())
        if record['csv_sha256'] != digest(job_path(job)):
            raise RuntimeError('completed CSV changed')
        print(f'DONE {job["id"]} wall={time.time()-start:.1f}s compute={record["seconds"]:.1f}s '
              f'estimate={job["estimate_seconds"]:.1f}s', flush=True)
    print('E1 COMPLETE', flush=True)


if __name__ == '__main__':
    main()
