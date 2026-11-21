#!/usr/bin/env python3
"""Replace a STOP-paused legacy login driver only after its compute job finishes."""
import argparse
import json
import os
import pathlib
import signal
import subprocess
import time

from e1_common import OUT, ROOT, digest, load_manifest, read_rows, validate_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pid', type=int)
    parser.add_argument('job')
    args = parser.parse_args()
    proc = pathlib.Path('/proc') / str(args.pid)
    if 'e1_driver.py' not in (proc / 'cmdline').read_text():
        raise RuntimeError('PID is not the legacy E1 driver')
    state = next(line for line in (proc / 'status').read_text().splitlines() if line.startswith('State:'))
    if 'T (stopped)' not in state:
        raise RuntimeError('pause only the login parent with SIGSTOP before attempting transition')
    if subprocess.check_output(['squeue', '-h', '-u', os.environ['USER']], text=True).strip():
        raise RuntimeError('compute job still active; leave the paused parent and retry later')
    if (OUT / 'STOPPED').exists():
        raise RuntimeError('E1 STOPPED flag present')
    job = next(j for j in load_manifest()['jobs'] if j['id'] == args.job)
    path = OUT / (job['id'] + '.csv')
    validate_rows(read_rows(path), len(job['sources']) * len(job['deltas']) * job['reps'])
    if digest(path) != json.loads(path.with_suffix('.done').read_text())['csv_sha256']:
        raise RuntimeError('current E1 job digest mismatch')
    print('SAFE BOUNDARY: E1 current job verified, SHA matches, scheduler empty', flush=True)
    os.kill(args.pid, signal.SIGTERM)
    os.kill(args.pid, signal.SIGCONT)
    for _ in range(100):
        if not proc.exists():
            break
        time.sleep(0.05)
    else:
        raise RuntimeError('old driver has not exited; refusing second driver')
    with (OUT / 'driver.log').open('ab') as log:
        new = subprocess.Popen(['nohup', 'python3', 'scripts/exp/e1_driver.py'], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    print(f'NEW_DRIVER_PID {new.pid}', flush=True)


if __name__ == '__main__':
    main()
