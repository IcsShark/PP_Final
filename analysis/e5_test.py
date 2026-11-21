import csv
import pathlib
import tempfile
import unittest

from e5_analysis import EVENTS, collect, metrics, read_aggregate, read_perf, read_timing, subtract
from e5_report import conclusions


class E5MathTest(unittest.TestCase):
    def test_independent_medians_and_twenty_extra_sssp_runs(self):
        self.assertAlmostEqual(subtract([100, 1, 2], [101, 3, 100]), 4.9)

    def test_invalid_or_empty_subtraction(self):
        for a, b in (([], []), ([1], [2]), ([1] * 3, [1] * 3),
                     ([2] * 3, [1] * 3), ([float('nan')] * 3, [3] * 3),
                     ([1] * 3, [float('inf')] * 3)):
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                subtract(a, b)

    def test_derived_metrics_units_and_stall_fractions(self):
        counts = dict(zip(EVENTS, (200, 100, 50, 10, 50, 100, 10, 20)))
        actual = metrics(counts, 2, 2)
        self.assertEqual(actual['cpi'], 2)
        self.assertEqual(actual['misses_per_edge'], 5)
        self.assertEqual(actual['miss_rate'], 0.2)
        self.assertEqual(actual['dram_gb_s'], 0.00032)
        self.assertEqual(actual['stall_l3_fraction'], 0.25)
        self.assertEqual(actual['stall_mem_fraction'], 0.5)
        for edges, time in ((0, 2), (2, 0), (-2, 2), (2, float('nan'))):
            with self.assertRaises(ValueError):
                metrics(counts, edges, time)

    def test_perf_scaled_counts_running_percentage_and_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'sample.perf'
            valid = '# perf header\n' + '\n'.join(f'100,,{event},1000,50.00,,' for event in EVENTS)
            path.write_text(valid)
            counts, percent = read_perf(path)
            self.assertEqual(counts, dict.fromkeys(EVENTS, 100))
            self.assertEqual(percent, 50)
            for content in ('', valid.replace('100,,cycles,', '<not supported>,,cycles,'),
                            valid + '\n100,,cycles,1000,50.00,,', valid.replace(',50.00,', ',101,')):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    read_perf(path)

    def test_time_is_mean_source_medians_not_process_elapsed_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'sample.csv'
            fields = ('source', 'rep', 'time_ms', 'verified', 'stats_build', 'variant',
                      'filter', 'sched', 'delta', 'threads', 'algo')
            rows = [dict(source=str(source), rep=str(rep), time_ms=str(source * 10 + rep),
                         verified='-1', stats_build='0', variant='all', filter='merge',
                         sched='dynamic:64', delta='4096', threads='1', algo='delta-omp')
                    for source in range(1, 5) for rep in range(6)]

            def write(data):
                with path.open('w') as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(data)

            write(rows)
            time, sources, settings = read_timing(path, 6)
            self.assertEqual(time, 27.5)
            self.assertEqual(sources, ('1', '2', '3', '4'))
            self.assertEqual(settings, ('all', 'merge', 'dynamic:64', '4096', '1', 'delta-omp'))
            for data in ([], rows[:-1], [{**r, 'verified': '0'} for r in rows],
                         [{**r, 'stats_build': '1'} for r in rows],
                         [{**r, 'rep': '0'} for r in rows]):
                write(data)
                with self.assertRaises(ValueError):
                    read_timing(path, 6)

    def test_collect_rejects_empty_campaign(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'No completed'):
                collect(pathlib.Path(directory))

    def test_report_rejects_empty_campaign(self):
        with self.assertRaises(ValueError):
            conclusions([])

    def test_aggregate_roundtrip_types_and_invalid_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'aggregate.csv'
            path.write_text('graph,threads,delta,time_ms,timing_within_10pct\nLJ,1,4096,1000,True\n')
            self.assertEqual(read_aggregate(path), [dict(graph='LJ', threads=1, delta=4096,
                                                       time_ms=1000, timing_within_10pct=True)])
            for content in ('graph,threads\n', 'graph,time_ms\nLJ,nan\n',
                            'graph,timing_within_10pct\nLJ,maybe\n'):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    read_aggregate(path)

    def test_report_partial_campaign_and_deviation(self):
        row = dict(graph='LJ', threads=1, time_ms=1000, speedup_t1=1, cpi=2,
                   misses_per_edge=1, miss_rate=0.5, dram_gb_s=5, triad_gb_s=15.5,
                   stall_mem_fraction=0.4, timing_deviation_pct=15,
                   timing_within_10pct=False, e2_time_ms=1000 / 1.15,
                   min_event_running_pct=49)
        report = conclusions([row])
        self.assertIn('LJ** (partial)', report)
        self.assertIn('1/12 required and 0/12 optional', report)
        self.assertIn('LJ t1: +15.00%', report)
        self.assertIn('USA: not measured yet', report)


if __name__ == '__main__':
    unittest.main()
