#!/usr/bin/env python3
"""Audit completed graphs, summarize source-median times, and update the ETA."""
import argparse
import collections
import gzip
import json
import statistics

from e1_common import OUT, PHASE_HEADER, digest, job_path, load_manifest, read_rows, validate_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--graphs', nargs='+', default=['NY', 'LJ'])
    args = parser.parse_args()
    manifest = load_manifest()
    records = []
    remaining = []
    for job in manifest['jobs']:
        done = OUT / (job['id'] + '.done')
        if done.exists():
            record = json.loads(done.read_text())
            records.append((job, record))
        else:
            remaining.append(job)
    report = []
    all_times = collections.defaultdict(list)
    stats = collections.defaultdict(list)
    for graph in args.graphs:
        if any(j['graph'] == graph for j in remaining):
            raise RuntimeError(f'{graph} is incomplete')
        graph_rows = []
        logs = 0
        for job, record in records:
            if job['graph'] != graph:
                continue
            rows = read_rows(job_path(job))
            validate_rows(rows, len(job['sources']) * len(job['deltas']) * job['reps'])
            if digest(job_path(job)) != record['csv_sha256']:
                raise RuntimeError(f'CSV digest mismatch: {job["id"]}')
            graph_rows.extend(rows)
            for path in record['phase_logs']:
                with gzip.open(path, 'rt') as f:
                    header = f.readline().strip().split(',')
                    first = f.readline().strip().split(',')
                    if header != PHASE_HEADER or len(first) != len(header):
                        raise RuntimeError(f'invalid phase log: {path}')
                logs += 1
            for row in rows:
                if job['kind'] == 'timing':
                    key = (graph, row['algo'], int(row['threads']), row['variant'], row['filter'],
                           int(row['delta']), int(row['source']))
                    all_times[key].append(float(row['time_ms']))
                if job['kind'] == 'stats':
                    if any(int(row[k]) <= 0 for k in ('edges_scanned', 'expansions', 'relax_ok', 'reached', 'phases')):
                        raise RuntimeError(f'zero stats counter: {row}')
                    key = (graph, row['algo'], row['variant'], row['filter'], int(row['delta']))
                    stats[key].append(int(row['phases']))
        report.append(f'{graph}: {len(graph_rows)} verified rows; {logs} gzip phase headers/first rows checked')
        seconds = [r['seconds'] for j, r in records if j['graph'] == graph]
        estimated = sum(j['estimate_seconds'] for j, r in records if j['graph'] == graph)
        report.append(f'{graph}: jobs={len(seconds)} compute_minutes={sum(seconds)/60:.2f} '
                      f'max_job_minutes={max(seconds)/60:.2f} estimated_minutes={estimated/60:.2f}')
    aggregate = collections.defaultdict(list)
    for key, values in all_times.items():
        if len(values) != 3:
            raise RuntimeError(f'wrong repetition count: {key}')
        aggregate[key[:-1]].append(statistics.median(values))
    for graph in args.graphs:
        for algo, t in (('delta-seq', 1), ('delta-omp', 6), ('delta-omp', 12)):
            candidates = []
            for key, values in aggregate.items():
                if key[:3] == (graph, algo, t):
                    if len(values) != 4:
                        raise RuntimeError(f'wrong source count: {key}')
                    candidates.append((statistics.mean(values), key[3:]))
            ms, (variant, filt, delta) = min(candidates)
            report.append(f'BEST {graph} {algo} t={t} {variant}/{filt} delta={delta} '
                          f'mean_source_median_ms={ms:.4f}')
        for algo in ('delta-seq', 'delta-omp'):
            for variant in ('all', 'lh'):
                for filt in ('pop', 'merge'):
                    sweep = manifest['profiles'][graph]['sweep']
                    phases = [statistics.mean(stats[(graph, algo, variant, filt, d)]) for d in sweep]
                    increases = sum(b > a for a, b in zip(phases, phases[1:]))
                    report.append(f'PHASES {graph} {algo} {variant}/{filt}: '
                                  f'{phases[0]:.1f} -> {phases[-1]:.1f}; adjacent increases={increases}')
    ratio = sum(r['seconds'] for j, r in records) / sum(j['estimate_seconds'] for j, r in records)
    projected = sum(j['estimate_seconds'] for j in remaining) * ratio
    report.append(f'ETA: {len(remaining)} jobs remain, observed/model={ratio:.3f}, '
                  f'projected_compute_hours={projected/3600:.2f}; add scheduler/NFS overhead')
    text = '\n'.join(report) + '\n'
    (OUT / 'SANITY.txt').write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
