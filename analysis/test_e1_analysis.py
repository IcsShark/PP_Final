import csv
import json
import pathlib
import tempfile
import types
import unittest

from e1_analysis import Data, findings_markdown, last_passing, q4_rows, rounded_rules, sha, write_csv


class RuleTests(unittest.TestCase):
    def test_partial_summary_csv_and_empty_output(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / 'out.csv'
            write_csv(path, [{'phases': 4}, {'phases': 2, 'empty_expanded': 1}])
            with path.open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]['empty_expanded'], '')
            self.assertEqual(rows[1]['empty_expanded'], '1')
            write_csv(path, [])
            self.assertEqual(path.read_text(), '')

    def test_findings_pending_and_complete(self):
        data = types.SimpleNamespace(graphs=['G'], pending=['H'], phases={}, stats={1: {}})
        self.assertIn('Phase reductions are pending', findings_markdown(data, [], []))
        reduction = dict(comparison='largest_sweep_delta', graph='G', algo='delta-seq',
            variant='all', filter='pop', small_delta=1, larger_delta=4, phases_small=10,
            phases_large=2, empty_expanded_small=4, empty_expanded_large=0, empty_share=0.5)
        self.assertIn('50.00%', findings_markdown(data, [reduction], []))
        reduction['empty_share'] = None
        self.assertIn('N/A', findings_markdown(data, [reduction], []))

    def test_rounding_and_clamp(self):
        self.assertEqual(rounded_rules(dict(w_max=9, d_max=2, n=1, m=2)), [5, 5])
        self.assertEqual(rounded_rules(dict(w_max=1, d_max=10, n=1, m=10)), [1, 1])

    def test_last_passing_empty_and_nonmonotone(self):
        self.assertIsNone(last_passing([], {}, 1))
        self.assertIsNone(last_passing([1], {1: 2}, 1))
        self.assertEqual(last_passing([1, 2, 4], {1: 0, 2: 10, 4: 1}, 1), 4)

    def test_q4_selection_slowdown_and_t12_stats_proxy(self):
        data = types.SimpleNamespace(graphs=['G'], manifest={'profiles': {'G': {'sweep': [1, 2, 4, 8]}}})
        data.profile = lambda graph: dict(n=10, m=20, w_max=8, d_max=4)
        data.times, data.metrics = {}, {}
        for algo, t in (('delta-seq', 1), ('delta-omp', 6), ('delta-omp', 12)):
            for d, ms in ((1, 10), (2, 8), (4, 5), (8, 9)):
                data.times[('G', algo, t, 'all', 'pop', d)] = ms
                data.metrics[('G', algo, 1 if algo == 'delta-seq' else 6, 'all', 'pop', d)] = {
                    'overhead': {1: 0, 2: 5, 4: 50, 8: 500}[d]}
        data.best = lambda g, a, t: (5, (g, a, t, 'all', 'pop', 4))
        rows = q4_rows(data)
        self.assertEqual(len(rows), 24)
        seq = {r['rule']: r for r in rows if r['algo'] == 'delta-seq'}
        self.assertEqual(seq['W/d_max']['delta'], 2)
        self.assertAlmostEqual(seq['W/d_max']['slowdown'], 1.6)
        self.assertEqual(seq['overhead_alpha=0.1']['delta'], 1)
        self.assertEqual(seq['overhead_alpha=2']['delta'], 4)
        self.assertTrue(all(r['stats_threads'] == 6 for r in rows if r['threads'] == 12))


class InputTests(unittest.TestCase):
    def fixture(self, directory, failed=False, corrupt=False):
        root = pathlib.Path(directory)
        out = root / 'results/e1_delta_sweep'
        out.mkdir(parents=True)
        jobs = []
        for kind, algo in (('dijkstra_stats', 'dijkstra'), ('stats', 'delta-seq')):
            ident = kind + '_G'
            job = dict(id=ident, graph='G', kind=kind, sources=[0, 1, 2, 3], deltas=[1], reps=1)
            jobs.append(job)
            rows = []
            for source in range(4):
                baseline = 10 * (source + 1)
                rows.append(dict(graph='G', algo=algo, threads=1, variant='all', filter='pop', delta=1,
                    source=source, verified='0' if failed else '1', time_ms=1, stats_build=1,
                    edges_scanned=baseline if algo == 'dijkstra' else 2 * baseline,
                    expansions=20, reached=10, buckets=2, phases=4, heavy_passes=0))
            path = out / (ident + '.csv')
            with path.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            path.with_suffix('.done').write_text(json.dumps({'csv_sha256': 'wrong' if corrupt else sha(path)}))
        (out / 'jobs.json').write_text(json.dumps({'profiles': {'G': {}}, 'jobs': jobs}))
        return root, out

    def test_source_matched_normalization(self):
        with tempfile.TemporaryDirectory() as d:
            root, out = self.fixture(d)
            data = Data(out, root)
            metrics = data.metrics[('G', 'delta-seq', 1, 'all', 'pop', 1)]
            self.assertEqual(metrics['edge_ratio'], 2)
            self.assertEqual(metrics['expansion_ratio'], 2)
            self.assertEqual(metrics['overhead'], 35)

    def test_bad_verification_and_digest(self):
        for kwargs in ({'failed': True}, {'corrupt': True}):
            with tempfile.TemporaryDirectory() as d:
                root, out = self.fixture(d, **kwargs)
                with self.assertRaises(ValueError):
                    Data(out, root)

    def test_no_complete_graphs(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / 'jobs.json').write_text(json.dumps({'profiles': {}, 'jobs': []}))
            with self.assertRaises(ValueError):
                Data(root, root)


if __name__ == '__main__':
    unittest.main()
