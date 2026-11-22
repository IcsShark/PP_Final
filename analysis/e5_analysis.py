#!/usr/bin/env python3
"""E5 process-counter subtraction, kernel-time comparison, and figures."""
import argparse
import csv
import math
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVENTS = ('cycles', 'instructions', 'cache-references', 'cache-misses',
          'cycle_activity.stalls_l3_miss', 'cycle_activity.stalls_mem_any',
          'mem_load_retired.l3_miss', 'offcore_requests.all_data_rd')
TRIAD = {1: 15.5, 2: 18.3, 4: 20.3, 6: 19.7, 8: 18.9, 12: 18.5}
DELTAS = {'LJ': 4096, 'USA': 32768, 'OK': 1024, 'urand23': 1024}


def positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'Expected positive finite number, got {value}')
    return value


def subtract(a, b):
    if len(a) != 3 or len(b) != 3:
        raise ValueError('Exactly three A and three B measurements required')
    return positive((statistics.median(map(positive, b)) -
                     statistics.median(map(positive, a))) / 20)


def metrics(counts, edges, time_ms):
    cycles, instructions, references, misses = (positive(counts[k]) for k in EVENTS[:4])
    return dict(cpi=cycles / instructions, misses_per_edge=misses / positive(edges),
                miss_rate=misses / references, dram_gb_s=misses * 64 / (positive(time_ms) * 1e6),
                stall_l3_fraction=positive(counts[EVENTS[4]]) / cycles,
                stall_mem_fraction=positive(counts[EVENTS[5]]) / cycles)


def read_perf(path):
    counts, percentages = {}, []
    with path.open() as stream:
        for row in csv.reader(stream):
            if len(row) < 5 or row[2] not in EVENTS:
                continue
            if row[2] in counts:
                raise ValueError(f'Duplicate event in {path}: {row[2]}')
            counts[row[2]] = positive(row[0])
            percent = positive(row[4])
            if percent > 100:
                raise ValueError(f'Invalid running percentage in {path}: {percent}')
            percentages.append(percent)
    if set(counts) != set(EVENTS):
        raise ValueError(f'Missing or unsupported events in {path}: {set(EVENTS) - set(counts)}')
    return counts, min(percentages)


def read_timing(path, repetitions):
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 4 * repetitions or any(r['verified'] != '-1' or r['stats_build'] != '0' for r in rows):
        raise ValueError(f'Invalid row count, verification, or timing build in {path}')
    sources = sorted({r['source'] for r in rows})
    if len(sources) != 4:
        raise ValueError(f'Expected four sources in {path}')
    times = []
    for source in sources:
        source_rows = [r for r in rows if r['source'] == source]
        if {int(r['rep']) for r in source_rows} != set(range(repetitions)) or len(source_rows) != repetitions:
            raise ValueError(f'Invalid repetitions in {path}')
        times.append(statistics.median(positive(r['time_ms']) for r in source_rows))
    settings = {(r['variant'], r['filter'], r['sched'], r['delta'], r['threads'], r['algo']) for r in rows}
    if len(settings) != 1:
        raise ValueError(f'Inconsistent settings in {path}')
    return statistics.mean(times), tuple(sources), settings.pop()


def job_result(job):
    graph, threads = job.parent.name, int(job.name.removeprefix('t'))
    reference = []
    with (ROOT / 'results/e2_scaling/all_runs.csv').open() as stream:
        reference = [r for r in csv.DictReader(stream) if r['graph'] == graph and
                     int(r['delta']) == DELTAS[graph] and int(r['threads']) == threads]
    if len(reference) != 1:
        raise ValueError(f'Expected exactly one same-delta/thread E2 baseline: {graph}/{threads}')
    baseline = reference[0]
    expected_settings = (baseline['variant'], baseline['filter'], 'dynamic:64', str(DELTAS[graph]), str(threads), 'delta-omp')
    samples = {kind: [] for kind in ('A', 'B')}
    sources, timings, percentages = None, [], []
    for kind, repetitions in (('A', 1), ('B', 6)):
        for rep in (1, 2, 3):
            prefix = job / f'{kind}{rep}'
            counts, percentage = read_perf(prefix.with_suffix('.perf'))
            timing, actual_sources, settings = read_timing(prefix.with_suffix('.csv'), repetitions)
            if sources is not None and sources != actual_sources:
                raise ValueError(f'A/B source mismatch in {job}')
            sources = actual_sources
            if settings != expected_settings:
                raise ValueError(f'Settings differ from E2 in {prefix}: {settings}')
            samples[kind].append(counts)
            percentages.append(percentage)
            if kind == 'B':
                timings.append(timing)
    counts = {event: subtract([r[event] for r in samples['A']], [r[event] for r in samples['B']]) for event in EVENTS}
    time_ms = statistics.median(timings)
    deviation = (time_ms / positive(baseline['time_ms']) - 1) * 100
    result = dict(graph=graph, threads=threads, delta=DELTAS[graph], variant=baseline['variant'],
                  filter=baseline['filter'], schedule='dynamic,64', time_ms=time_ms,
                  e2_time_ms=float(baseline['time_ms']), timing_deviation_pct=deviation,
                  timing_within_10pct=abs(deviation) < 10, edges_scanned=float(baseline['edges_scanned']),
                  **{k.replace('-', '_').replace('.', '_'): v for k, v in counts.items()},
                  **metrics(counts, baseline['edges_scanned'], time_ms),
                  min_event_running_pct=min(percentages), triad_gb_s=TRIAD[threads],
                  hostname=(job / 'hostname.txt').read_text().strip(), sources=';'.join(sources),
                  raw_directory=str(job))
    return result


def collect(raw):
    rows = [job_result(job) for graph in DELTAS for job in sorted((raw / graph).glob('t*'),
            key=lambda p: int(p.name[1:])) if job.is_dir() and (job / 'DONE').exists()]
    if not rows:
        raise ValueError('No completed E5 jobs')
    baselines = {r['graph']: r['time_ms'] for r in rows if r['threads'] == 1}
    for row in rows:
        if row['graph'] not in baselines:
            raise ValueError(f'Missing same-delta t1 baseline for {row["graph"]}')
        with (raw / row['graph'] / 'verify.csv').open() as stream:
            verification = list(csv.DictReader(stream))
        if (len(verification) != 4 or
                any(r['verified'] != '1' or r['stats_build'] != '0' for r in verification) or
                ';'.join(sorted({r['source'] for r in verification})) != row['sources']):
            raise ValueError(f'Invalid graph verification for {row["graph"]}')
        row['speedup_t1'] = baselines[row['graph']] / row['time_ms']
    return rows


def read_aggregate(path):
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError('Empty E5 aggregate CSV')
    text_fields = {'graph', 'variant', 'filter', 'schedule', 'hostname', 'sources', 'raw_directory'}
    for row in rows:
        for key, value in row.items():
            if key in text_fields:
                continue
            if key == 'timing_within_10pct':
                if value not in ('True', 'False'):
                    raise ValueError(f'Invalid boolean: {value}')
                row[key] = value == 'True'
            elif key in ('threads', 'delta'):
                row[key] = int(value)
            else:
                row[key] = float(value)
                if not math.isfinite(row[key]):
                    raise ValueError(f'Invalid aggregate number: {key}={value}')
    return rows


def plot(rows, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plots = out / 'plots'
    plots.mkdir(exist_ok=True)
    caption = 'Estimated DRAM BW: lower bound, no prefetch/write-back; generic cache-misses proxy.'
    for graph in dict.fromkeys(r['graph'] for r in rows):
        data = [r for r in rows if r['graph'] == graph]
        t = [r['threads'] for r in data]
        fig, axes = plt.subplots(2, 2, figsize=(10, 7))
        ax = axes[0, 0]
        ax.plot(t, [r['time_ms'] for r in data], 'o-', label='Kernel time')
        ax.set_ylabel('Time (ms)')
        twin = ax.twinx()
        twin.plot(t, [r['speedup_t1'] for r in data], 's--', color='tab:orange', label='Same-Δ t1 speedup')
        twin.set_ylabel('Speedup')
        ax.set_title('Time and same-Δ speedup')
        ax, twin = axes[0, 1], None
        ax.plot(t, [r['cpi'] for r in data], 'o-')
        ax.axhline(1, color='gray', linestyle='--', label='CPI = 1')
        ax.set_ylabel('Cycles / instructions')
        ax.set_title('CPI (all OpenMP threads summed)')
        ax.legend(fontsize=8)
        ax = axes[1, 0]
        ax.plot(t, [r['misses_per_edge'] for r in data], 'o-', label='Misses/edge')
        ax.set_ylabel('Generic cache-misses / scanned edge')
        twin = ax.twinx()
        twin.plot(t, [100 * r['miss_rate'] for r in data], 's--', color='tab:orange')
        twin.set_ylabel('Miss rate (%)')
        ax.set_title('LLC proxy and cache-misses / references')
        ax = axes[1, 1]
        ax.plot(t, [r['dram_gb_s'] for r in data], 'o-', label='Misses × 64 B / kernel time')
        ax.plot(t, [r['triad_gb_s'] for r in data], '--', color='gray', label='Measured triad reference')
        ax.set_ylabel('GB/s (decimal)')
        ax.set_title('Estimated DRAM bandwidth')
        ax.legend(fontsize=8)
        for ax in axes.flat:
            ax.set_xticks(list(TRIAD))
            ax.set_xlabel('Threads')
            ax.grid(alpha=0.25)
        fig.suptitle(f'E5 {graph}: Δ={data[0]["delta"]}, {data[0]["variant"]}/{data[0]["filter"]}, dynamic,64')
        fig.text(0.5, 0.015, caption, ha='center', fontsize=8)
        fig.tight_layout(rect=(0, 0.04, 1, 0.95))
        for extension in ('pdf', 'png'):
            fig.savefig(plots / f'e5_{graph}.{extension}', dpi=110)
        plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for graph in dict.fromkeys(r['graph'] for r in rows):
        data = [r for r in rows if r['graph'] == graph]
        t = [r['threads'] for r in data]
        for ax, metric, title in zip(axes, ('cpi', 'dram_gb_s', 'stall_mem_fraction'),
                                    ('CPI', 'Estimated DRAM BW (GB/s)', 'Memory-stall cycles / cycles')):
            ax.plot(t, [r[metric] for r in data], 'o-', label=graph)
            ax.set_title(title)
            ax.set_xlabel('Threads')
            ax.set_xticks(list(TRIAD))
            ax.grid(alpha=0.25)
    axes[0].axhline(1, color='gray', linestyle='--')
    axes[1].plot(list(TRIAD), list(TRIAD.values()), '--', color='gray', label='Triad reference')
    for ax in axes:
        ax.legend(fontsize=8)
    fig.text(0.5, 0.02, caption, ha='center', fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    for extension in ('pdf', 'png'):
        fig.savefig(plots / f'e5_overlay.{extension}', dpi=110)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=pathlib.Path)
    parser.add_argument('--csv-input', type=pathlib.Path)
    parser.add_argument('--out', type=pathlib.Path, default=ROOT / 'results/e5_perf')
    parser.add_argument('--check-job', type=pathlib.Path)
    parser.add_argument('--csv-only', action='store_true')
    args = parser.parse_args()
    if args.check_job:
        row = job_result(args.check_job)
        print(f'PASS: {row["graph"]} t={row["threads"]}: 3 A + 3 B, same sources, eight usable events; '
              f'time={row["time_ms"]:.3f} ms, E2 deviation={row["timing_deviation_pct"]:+.2f}%')
        return
    if (args.raw is None) == (args.csv_input is None):
        parser.error('Specify exactly one of --raw or --csv-input (or use --check-job)')
    rows = collect(args.raw) if args.raw else read_aggregate(args.csv_input)
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / 'e5_counters.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    if not args.csv_only:
        plot(rows, args.out)
    print(f'PASS: {len(rows)} E5 combinations; {sum(not r["timing_within_10pct"] for r in rows)} timing deviations >=10%')


if __name__ == '__main__':
    main()
