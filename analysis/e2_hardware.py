"""Descriptive nonnegative work/phase fits and assumed 72-byte edge traffic."""
import itertools
import math

import numpy as np


def bandwidth_gbs(edges, time_ms):
    if not all(math.isfinite(x) for x in (edges, time_ms)) or edges < 0 or time_ms <= 0:
        raise ValueError('bandwidth needs finite nonnegative edges and positive time')
    return edges * 72 / time_ms / 1e6


def design(rows, threads):
    if not rows:
        raise ValueError('no work/sync observations')
    matrix, times = [], []
    for row in rows:
        work, phases, ms = (float(row[k]) for k in ('ideal_work', 'phases', 'time_ms'))
        if not all(math.isfinite(x) for x in (work, phases, ms)) or work < 0 or phases <= 0 or ms <= 0:
            raise ValueError('invalid work/sync observation')
        if row['threads'] not in threads:
            raise ValueError('unknown thread count')
        matrix.append([work] + [phases if row['threads'] == k else 0 for k in threads])
        times.append(ms)
    return np.asarray(matrix), np.asarray(times)


def nonnegative_fit(matrix, times):
    scales = np.linalg.norm(matrix, axis=0)
    if np.any(scales == 0):
        raise ValueError('unobserved work/sync coefficient')
    normalized = matrix / scales
    best, loss = np.zeros(matrix.shape[1]), float(np.dot(times, times))
    for count in range(1, matrix.shape[1] + 1):
        for active in itertools.combinations(range(matrix.shape[1]), count):
            part = normalized[:, active]
            values = np.linalg.lstsq(part, times, rcond=None)[0]
            if np.any(values < 0):
                continue
            residual = times - part @ values
            candidate = float(np.dot(residual, residual))
            if candidate < loss:
                best = np.zeros(matrix.shape[1])
                best[list(active)] = values / scales[list(active)]
                loss = candidate
    return best


def fit(rows):
    threads = sorted({r['threads'] for r in rows})
    matrix, times = design(rows, threads)
    coefficients = nonnegative_fit(matrix, times)
    residual = times - matrix @ coefficients
    squared = float(np.dot(residual, residual))
    variance = float(np.sum((times - times.mean()) ** 2))
    normalized = matrix / np.linalg.norm(matrix, axis=0)
    rank = int(np.linalg.matrix_rank(normalized))
    return dict(threads=threads, coefficients=coefficients, observations=len(rows), parameters=len(coefficients),
        rank=rank, condition_number=float(np.linalg.cond(normalized)),
        identifiable=rank == len(coefficients), rmse_ms=math.sqrt(squared / len(rows)),
        r_squared=1 - squared / variance if variance > 0 else None,
        mean_absolute_percent_error=100 * float(np.mean(np.abs(residual) / times)),
        relative_rmse_percent=100 * math.sqrt(squared / len(rows)) / float(times.mean()))


def leave_delta_out_rmse(rows):
    deltas = sorted({r['delta'] for r in rows})
    if len(deltas) < 3:
        return None
    errors = []
    for delta in deltas:
        train = [r for r in rows if r['delta'] != delta]
        test = [r for r in rows if r['delta'] == delta]
        result = fit(train)
        if not result['identifiable']:
            return None
        matrix, times = design(test, result['threads'])
        errors.extend(times - matrix @ result['coefficients'])
    return math.sqrt(float(np.mean(np.square(errors))))


def analyze(rows, best):
    if not rows:
        raise ValueError('no complete E2 observations')
    fits, splits, bandwidth = [], [], []
    for graph in sorted({r['graph'] for r in rows}):
        observations = [r for r in rows if r['graph'] == graph]
        result = fit(observations)
        coefficients = result.pop('coefficients')
        threads = result.pop('threads')
        result.update(graph=graph, c_edge_ns=1e6 * coefficients[0],
            leave_delta_out_rmse_ms=leave_delta_out_rmse(observations))
        result.update({f'c_sync_t{k}_ns': 1e6 * coefficients[i+1] for i, k in enumerate(threads)})
        fits.append(result)
        for row in best:
            if row['graph'] != graph or row['threads'] not in (1, 6, 12):
                continue
            k = row['threads']
            work = coefficients[0] * row['ideal_work']
            sync = coefficients[threads.index(k)+1] * row['phases']
            predicted = work + sync
            splits.append(dict(graph=graph, threads=k, delta=row['delta'], measured_ms=row['time_ms'],
                fitted_ms=predicted, work_ms=work, sync_ms=sync,
                work_percent=100*work/predicted if predicted else None,
                sync_percent=100*sync/predicted if predicted else None,
                residual_ms=row['time_ms']-predicted))
            if k in (6, 12):
                rate = bandwidth_gbs(row['edges_scanned'], row['time_ms'])
                bandwidth.append(dict(graph=graph, threads=k, delta=row['delta'], edges_scanned=row['edges_scanned'],
                    time_ms=row['time_ms'], assumed_bytes_per_edge=72, effective_gbs=rate,
                    triad_reference_gbs=20, fraction_of_triad=rate/20))
    return fits, splits, bandwidth


def markdown(fits, splits, bandwidth):
    def number(value):
        return 'N/A' if value is None else f'{value:.3f}'
    lines = ['# Q3 work/phase model and effective bandwidth', '',
        'Per graph, nonnegative least squares fits T(k,Δ) = c_edge × mean_source(Tideal_k) '
        '+ c_sync(k) × mean_source(phases). One c_edge is shared across threads; each k has its own c_sync. '
        'Observations are all frozen E2 Δ/thread points; times are means of four source-wise medians. '
        'This is an in-sample descriptive fit, not a measurement of barrier time: the phase term can absorb '
        'bucket processing, memory, filtering, imbalance and other omitted costs. Both terms may be correlated. '
        'Percent splits divide fitted, not measured, time; measured minus fitted is shown separately. '
        'Leave-one-Δ-out RMSE refits on the other Δ values; it is unavailable with fewer than three Δ values '
        'or rank-deficient training designs. No new cluster measurements are used.', '',
        '| Graph | Points / parameters | Rank | Scaled condition | R² | RMSE ms | Relative RMSE % | LODO RMSE ms | c_edge ns |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in fits:
        lines.append(f'| {r["graph"]} | {r["observations"]}/{r["parameters"]} | {r["rank"]} | '
            f'{number(r["condition_number"])} | {number(r["r_squared"])} | {number(r["rmse_ms"])} | '
            f'{number(r["relative_rmse_percent"])} | {number(r["leave_delta_out_rmse_ms"])} | {number(r["c_edge_ns"])} |')
    lines += ['', '| Graph | t | Δ | Measured ms | Fitted ms | Work ms (%) | Phase/sync ms (%) | Residual ms |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in splits:
        lines.append(f'| {r["graph"]} | {r["threads"]} | {r["delta"]} | {r["measured_ms"]:.3f} | '
            f'{r["fitted_ms"]:.3f} | {r["work_ms"]:.3f} ({number(r["work_percent"])}) | '
            f'{r["sync_ms"]:.3f} ({number(r["sync_percent"])}) | {r["residual_ms"]:.3f} |')
    lines += ['', 'Effective traffic bound = mean_source(edges_scanned) × (8 + 64) bytes / mean-source-median time, '
        'in decimal GB/s. This assumes one 8-byte edge read plus a whole 64-byte destination-distance cache line '
        'per scan with no reuse. It is not measured DRAM traffic or a bound on all traffic: it omits, for example, '
        'bucket writes and extra coherence traffic. Values near or above the approximate 20 GB/s triad reference '
        'are consistent with cache reuse and/or memory pressure, not proof of bandwidth saturation or latency limitation.', '',
        '| Graph | t | Δ | Assumed effective GB/s | /20 GB/s |', '|---|---:|---:|---:|---:|']
    for r in bandwidth:
        lines.append(f'| {r["graph"]} | {r["threads"]} | {r["delta"]} | {r["effective_gbs"]:.3f} | {r["fraction_of_triad"]:.3f} |')
    return '\n'.join(lines) + '\n'
