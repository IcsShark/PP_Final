#!/usr/bin/env python3
import csv
import hashlib
import json
import math
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/e1_delta_sweep'
RAW = pathlib.Path.home() / 'devin/results_raw/e1'
DATA = pathlib.Path('/u/cs/111/111550055/pp_data/csr')
ORDER = ('NY', 'LJ', 'grid2896', 'CTR', 'USA', 'kron23', 'urand23', 'OK')
PHASE_HEADER = ['graph', 'algo', 'variant', 'filter', 'threads', 'delta', 'source',
                'phase', 'bucket', 'heavy', 'frontier', 'expanded', 'edges', 'max_vertex_edges']


def revision():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest():
    return json.loads((OUT / 'jobs.json').read_text())


def read_rows(path):
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def validate_rows(rows, expected=None):
    if expected is not None and len(rows) != expected:
        raise RuntimeError(f'expected {expected} rows, got {len(rows)}')
    for row in rows:
        if row.get('verified') != '1':
            raise RuntimeError(f'unverified or WRONG row: {row}')
        if not row.get('time_ms') or not math.isfinite(float(row['time_ms'])) or float(row['time_ms']) < 0:
            raise RuntimeError(f'invalid timing row: {row}')


def job_path(job):
    return OUT / (job['id'] + '.csv')
