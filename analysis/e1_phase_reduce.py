#!/usr/bin/env python3
"""Streaming gzip reduction, run on compute nodes; raw phase logs never enter Git."""
import argparse
import csv
import gzip
import json
import os
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/e1_delta_sweep/phase_summaries'
HEADER = ['graph', 'algo', 'variant', 'filter', 'threads', 'delta', 'source',
          'phase', 'bucket', 'heavy', 'frontier', 'expanded', 'edges', 'max_vertex_edges']
KEYS = HEADER[:7]
COUNTERS = ('phases', 'empty_frontier', 'empty_expanded', 'empty_edges',
            'heavy_phases', 'frontier_sum', 'expanded_sum', 'edges_sum')


def summarize(stream):
    reader = csv.reader(stream)
    if next(reader, None) != HEADER:
        raise ValueError('invalid or missing phase-log header')
    records = []
    current = None
    seen = set()
    for row in reader:
        if len(row) != len(HEADER):
            raise ValueError('malformed phase-log row')
        key = tuple(row[:7])
        if key != current:
            if key in seen:
                raise ValueError('non-contiguous or duplicate phase run')
            seen.add(key)
            current = key
            record = dict(zip(KEYS, key))
            record.update(dict.fromkeys(COUNTERS, 0))
            records.append(record)
        if int(row[7]) != record['phases']:
            raise ValueError('missing or duplicate phase index')
        frontier, expanded, edges = map(int, row[10:13])
        if min(frontier, expanded, edges) < 0 or expanded > frontier:
            raise ValueError('invalid phase counters')
        record['phases'] += 1
        record['empty_frontier'] += frontier == 0
        record['empty_expanded'] += expanded == 0
        record['empty_edges'] += edges == 0
        record['heavy_phases'] += int(row[9])
        record['frontier_sum'] += frontier
        record['expanded_sum'] += expanded
        record['edges_sum'] += edges
    if not records:
        raise ValueError('empty phase log')
    return records


def cached(path):
    output = OUT / (path.name + '.json')
    if not output.exists():
        return False
    record = json.loads(output.read_text())
    st = path.stat()
    return record['version'] == 1 and record['size'] == st.st_size and record['mtime_ns'] == st.st_mtime_ns


def reduce_file(path):
    st = path.stat()
    start = time.monotonic()
    with gzip.open(path, 'rt', newline='') as f:
        rows = summarize(f)
    payload = dict(version=1, path=str(path), size=st.st_size, mtime_ns=st.st_mtime_ns,
                   reduction_seconds=time.monotonic() - start, rows=rows)
    output = OUT / (path.name + '.json')
    temporary = output.with_suffix('.json.partial')
    temporary.write_text(json.dumps(payload, indent=2) + '\n')
    os.replace(temporary, output)
    print(f'Reduced {path.name}: {sum(r["phases"] for r in rows)} phases in '
          f'{payload["reduction_seconds"]:.2f}s', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', nargs='*', type=pathlib.Path, default=[])
    parser.add_argument('--backlog-graphs', nargs='*', default=['NY', 'LJ'])
    parser.add_argument('--budget-seconds', type=float, default=90)
    parser.add_argument('--max-files', type=int, default=24)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    paths = list(args.files)
    for marker in sorted((ROOT / 'results/e1_delta_sweep').glob('stats_*.done')):
        record = json.loads(marker.read_text())
        if any(f'_{g}_' in record['job'] for g in args.backlog_graphs):
            paths.extend(map(pathlib.Path, record['phase_logs']))
    count = 0
    for path in dict.fromkeys(paths):
        if cached(path):
            continue
        if count >= args.max_files or time.monotonic() - start >= args.budget_seconds:
            break
        reduce_file(path)
        count += 1
    print(f'Phase reduction: {count} new files, {time.monotonic()-start:.2f}s', flush=True)


if __name__ == '__main__':
    main()
