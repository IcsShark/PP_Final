#!/usr/bin/env python3
"""Lightweight login-node progress and observed/model E1 ETA snapshot."""
import json
import re
import statistics

from e1_common import OUT as E1, load_manifest
from e2_plan import OUT as E2


def main():
    jobs = load_manifest()['jobs']
    completed = [(j, json.loads((E1 / (j['id'] + '.done')).read_text())) for j in jobs
                 if (E1 / (j['id'] + '.done')).exists()]
    ids = {j['id'] for j, r in completed}
    remaining = [j for j in jobs if j['id'] not in ids]
    ratio = sum(r['seconds'] for j, r in completed) / sum(j['estimate_seconds'] for j, r in completed)
    result = dict(e1_complete=len(completed), e1_remaining=len(remaining), observed_model_ratio=ratio,
                  e1_remaining_compute_hours=ratio*sum(j['estimate_seconds'] for j in remaining)/3600,
                  note='E1 model extrapolation only; add E2 and scheduler/NFS time', e2={})
    wall = {name: float(seconds) for name, seconds in re.findall(r'DONE (\S+) wall=([0-9.]+)s',
                                                               (E1 / 'driver.log').read_text())}
    for path in sorted(E2.glob('*.json')):
        plan = json.loads(path.read_text())
        if not isinstance(plan, dict) or 'jobs' not in plan:
            continue
        js = plan['jobs']
        records = [json.loads((E2 / (j['id'] + '.done')).read_text()) for j in js
                   if (E2 / (j['id'] + '.done')).exists()]
        times = [wall[j['id']] for j in js if j['id'] in wall]
        result['e2'][plan['graph']] = dict(complete=len(records), jobs=len(js),
            compute_minutes=sum(r['seconds'] for r in records)/60, wall_minutes=sum(times)/60,
            mean_completed_job_wall_seconds=statistics.mean(times) if times else None)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
