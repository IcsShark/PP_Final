#!/usr/bin/env python3
"""Render E5 provenance and factual conclusion tables from completed jobs."""
import argparse
import hashlib
import pathlib
import subprocess

from e5_analysis import DELTAS, EVENTS, ROOT, TRIAD, collect


def conclusions(rows):
    if not rows:
        raise ValueError('Cannot summarize an empty campaign')
    lines = ['# E5 hardware counters', '',
             'Counter estimates use (median(B) − median(A)) / 20, independently per event, '
             'from three A and three B process measurements. B has 24 SSSP calls; A has four. '
             'Kernel time is the median across three B invocations of the mean of four '
             'source-wise medians. Speedup uses the same graph/Δ t1.', '',
             '## Measurements', '',
             '| Graph | t | Time ms | Speedup | CPI | Misses/edge | Miss rate | BW GB/s | Triad GB/s | Memory stall | E2 deviation |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f'| {r["graph"]} | {r["threads"]} | {r["time_ms"]:.3f} | {r["speedup_t1"]:.3f}× '
                     f'| {r["cpi"]:.3f} | {r["misses_per_edge"]:.3f} | {r["miss_rate"]:.1%} '
                     f'| {r["dram_gb_s"]:.3f} | {r["triad_gb_s"]:.1f} | {r["stall_mem_fraction"]:.1%} '
                     f'| {r["timing_deviation_pct"]:+.2f}% |')
    lines += ['', '## Conclusions from these measurements', '']
    by_graph = {graph: [r for r in rows if r['graph'] == graph] for graph in DELTAS}
    for graph, data in by_graph.items():
        if not data:
            lines.append(f'- {graph}: not measured yet (optional for OK and urand23).')
            continue
        low, high = data[0], data[-1]
        complete = {r['threads'] for r in data} == set(TRIAD)
        crosses = [str(r['threads']) for r in data if r['dram_gb_s'] >= r['triad_gb_s']]
        lines.append(f'- **{graph}** ({"complete" if complete else "partial"}): CPI '
                     f'{low["cpi"]:.3f} at t={low["threads"]} → {high["cpi"]:.3f} at t={high["threads"]}; '
                     f'estimated bandwidth {low["dram_gb_s"]:.3f} → {high["dram_gb_s"]:.3f} GB/s. '
                     f'The estimate reaches/exceeds the same-thread triad reference at '
                     f'{", ".join(crosses) if crosses else "none of the measured thread counts"}.')
        if complete:
            six = next(r for r in data if r['threads'] == 6)
            twelve = next(r for r in data if r['threads'] == 12)
            lines.append(f'  t6→t12 speedup is only {six["time_ms"] / twelve["time_ms"]:.3f}×; '
                         f't12 efficiency versus same-Δ t1 is {twelve["speedup_t1"] / 12:.1%}. '
                         f'All measured CPI values exceed one: {all(r["cpi"] > 1 for r in data)}. '
                         f'CPI increases monotonically: {all(a["cpi"] <= b["cpi"] for a, b in zip(data, data[1:]))}.')
    if by_graph['LJ'] and by_graph['USA']:
        lj, usa = by_graph['LJ'][-1], by_graph['USA'][-1]
        lines.append(f'- **Road/social comparison**: at the highest measured threads '
                     f'(LJ t{lj["threads"]}, USA t{usa["threads"]}), USA CPI {usa["cpi"]:.3f} '
                     f'vs LJ {lj["cpi"]:.3f}; USA bandwidth {usa["dram_gb_s"]:.3f} '
                     f'vs LJ {lj["dram_gb_s"]:.3f} GB/s. '
                     'Use these observed values, not an assumption that the road CPI must be lower.')
    lines += ['', '### Interpretation limits', '',
              '- High CPI, saturation and memory-stall events are consistent with memory pressure, '
              'but do not by themselves prove a bandwidth bottleneck. CPI also includes spinning '
              'and instructions outside the timed SSSP kernel. A low bandwidth estimate with high '
              'CPI is consistent with latency limits, but cannot establish latency rather than '
              'synchronization or insufficient memory-level parallelism. This applies to optional urand23 too.',
              '- These process-wide counters do not measure barrier time. Thus E5 alone cannot '
              'establish "road graph sync-bound". The existing E2 work/phase fit is descriptive, '
              'not a direct synchronization measurement.',
              '- LLC-load-misses is unavailable. The required generic cache-misses counter is an '
              'LLC proxy, not a validated count of demand DRAM reads. Estimated DRAM BW: '
              '**lower bound, no prefetch/write-back**, as prescribed by the spec; this is a '
              'traffic-accounting assumption, not a strict bound on physical DRAM traffic. Cache '
              'line transfers can include cache/coherence effects. Retired L3-miss and offcore '
              'counts are also retained in the CSV; offcore requests are not all DRAM reads.',
              '- Perf scales multiplexed events independently; subtraction amplifies sampling '
              'and run-to-run error. Counts include repeated per-source/SSSP housekeeping outside '
              'the kernel timer (e.g. reached-vertex scans), not only edge relaxation. The load '
              'subtraction removes fixed process costs statistically, not exactly.',
              '- A separate timing-build verification run per graph is outside the perf '
              'measurements; this avoids charging Dijkstra and verification scans to the counters. '
              'The measured CSV verified=-1 means verification was not requested, not a failure. '
              'Verification CSV rows must all be verified=1.',
              '- Edges scanned and E2 timings come from the exact same graph/Δ/thread setting '
              'in results/e2_scaling/all_runs.csv. Thread-dependent work can vary. All runs use '
              'seed 42, four sources, the frozen E2 variant/filter and dynamic,64 schedule.',
              '- Triad GB/s references: ' + ', '.join(f't{k}={v}' for k, v in TRIAD.items()) +
              '; DRAM random-access latency reference ≈67 ns. Neither was remeasured.',
              '- Guest reports Intel i5-10500/KVM, 12 cores × 1 thread, 16 MiB L3. '
              'Whole-node run -c 12 is used even for t1. The guest topology is not evidence of SMT placement.',
              '- Prior teammate-reported LJ CSR corruption remains a caveat; verification is '
              'against Dijkstra on the same read-only input, not an independent clean graph.', '',
              '## Anomalies and completeness', '']
    deviations = [r for r in rows if not r['timing_within_10pct']]
    required = sum(r['graph'] in ('LJ', 'USA') for r in rows)
    lines.append(f'- Completed {required}/12 required and {len(rows) - required}/12 optional combinations; '
                 f'{len(deviations)} timings differ from same-Δ E2 by at least 10%.')
    for r in deviations:
        lines.append(f'  - {r["graph"]} t{r["threads"]}: {r["timing_deviation_pct"]:+.2f}% '
                     f'({r["time_ms"]:.3f} vs {r["e2_time_ms"]:.3f} ms). Retained without retuning.')
    lines.append(f'- Minimum event running percentage: {min(r["min_event_running_pct"] for r in rows):.2f}%. '
                 'All eight events must be finite, positive and present in all six samples.')
    return '\n'.join(lines) + '\n'


def provenance(rows, raw):
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    lines = ['E5 hardware-counter experiment', f'Metadata generation HEAD: {sha}',
             'Build source commit: b97aec1c8c5b8afacd7c3dc8e4a445bebf015c65 (fetched upstream main)',
             'Branch: exp/e5-perf; publication remote: fork (Penguin-71630/PP_Final); never main.',
             'Cluster worktree: /u/cs/111/111550055/devin/PP_Final',
             'Previous untracked experiment tree preserved intact at:',
             '/u/cs/111/111550055/devin/PP_Final.pre-e5-1795262155',
             f'Raw .perf/.csv, job logs, probe/build logs and DONE/verification markers: {raw}',
             'Raw files are outside Git. Only aggregate CSV, metadata, summary and figures are published.',
             'Required settings: LJ Δ4096 all/merge; USA Δ32768 all/pop.',
             'Optional settings: OK Δ1024 all/merge; urand23 Δ1024 all/merge.',
             'All: dynamic,64 (E2 worker default, confirmed against CLI help); seed42; four sources;',
             't=1,2,4,6,8,12; A=-r1, B=-r6; three repetitions of each.',
             'Counter = (median of three B counts - median of three A counts)/20, per event.',
             'Time = median of three B mean(source-wise medians), milliseconds; same as E2 aggregation.',
             'Edges scanned = same graph/Δ/t E2 all_runs.csv; denominator is mean over four sources.',
             'Events: ' + ','.join(EVENTS),
             'Both stall events, retired L3 misses and offcore reads returned positive numeric probe counts.',
             'LLC-load-misses: UNSUPPORTED in actual perf stat probe, despite generic perf-list catalogs.',
             'All eight campaign events are checked in every A/B sample; numeric perf counts are already scaled.',
             'All OpenMP threads summed by perf default; raw event running percentages retained.',
             'Triad reference, decimal GB/s: ' + ', '.join(f't{k}={v}' for k, v in TRIAD.items()),
             'DRAM random-access latency reference: approximately 67 ns (not remeasured).',
             'Estimated DRAM BW = cache-misses *64 / (kernel_time_ms*1e6) GB/s;',
             'lower bound, no prefetch/write-back (assumption; see SUMMARY limitations).',
             'CPI=cycles/instructions; misses/edge=cache-misses/edges_scanned;',
             'miss_rate=cache-misses/cache-references; stall fractions=stall cycles/cycles.',
             'OMP_PROC_BIND and OMP_PLACES unset, as in E2; allocation >= threads.',
             'One QoS job at a time, flock + empty-scheduler check, timeout1700s per measurement job.',
             'Verification is separate from perf A/B; any verified=0, WRONG or MISMATCH stops execution.',
             '', 'Reproduction (module load pp before all cluster operations):',
             'module load pp', 'bash scripts/exp/e5_probe.sh',
             'run -c 12 -- bash scripts/exp/e5_probe.sh --events',
             'bash scripts/exp/e5_run.sh', 'bash scripts/exp/e5_run.sh --optional',
             f'python3 analysis/e5_analysis.py --raw {raw}',
             f'python3 analysis/e5_report.py --raw {raw}',
             'Build command: run -c 4 -- make -j4',
             'Inventory command: run -c 12 -- bash scripts/exp/e5_probe.sh --compute',
             'Per-combo scheduler command: run -c 12 -- timeout 1700 bash scripts/exp/e5_run.sh --compute GRAPH THREADS',
             '', 'Input/script SHA256:']
    for relative in ('scripts/exp/e5_run.sh', 'scripts/exp/e5_probe.sh', 'analysis/e5_analysis.py',
                     'analysis/e5_report.py', 'results/e2_scaling/all_runs.csv'):
        lines.append(f'{hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()}  {relative}')
    lines += ['', 'Probe host/hardware/affinity/environment and exact executed commands:',
              (raw / 'probe.log').read_text(), '', 'Advanced-event probes:',
              (raw / 'extra_events.log').read_text(), '', 'Completed measurement job commands:']
    for row in rows:
        job = pathlib.Path(row['raw_directory'])
        log = (job / 'job.log').read_text().splitlines()
        lines += [f'{row["graph"]} t{row["threads"]}; host={row["hostname"]}; sources={row["sources"]}',
                  'run -c 12 -- timeout 1700 bash scripts/exp/e5_run.sh --compute '
                  f'{row["graph"]} {row["threads"]}']
        lines += [line for line in log if line.startswith(('perf ', './bin/sssp ', '2026-', 'OMP_', 'pid '))]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=pathlib.Path, required=True)
    parser.add_argument('--out', type=pathlib.Path, default=ROOT / 'results/e5_perf')
    args = parser.parse_args()
    rows = collect(args.raw)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'SUMMARY.md').write_text(conclusions(rows))
    (args.out / 'META.txt').write_text(provenance(rows, args.raw))
    print(f'PASS: E5 report generated for {len(rows)} combinations')


if __name__ == '__main__':
    main()
