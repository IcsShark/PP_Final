import csv
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import e2_plan
from e1_common import digest
from e2_plan import neighbours, prepare
from e2_driver import choose


class PlanTests(unittest.TestCase):
    def test_neighbours(self):
        self.assertEqual(neighbours(4, [1, 2, 4, 8]), [2, 4, 8])
        self.assertEqual(neighbours(3, [1, 2, 4, 8]), [2, 3, 4])
        self.assertEqual(neighbours(1, [1, 2, 4]), [1, 2])
        self.assertEqual(neighbours(1, []), [1])

    def test_prepare_incomplete_empty(self):
        with tempfile.TemporaryDirectory() as d, patch.object(e2_plan, 'OUT', pathlib.Path(d)):
            self.assertIsNone(prepare('G', {'jobs': []}))
            self.assertIsNone(prepare('G', {'jobs': [{'id': 'missing', 'graph': 'G'}]}))

    def test_selection_deduplication_and_digest(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            e1, out = root / 'e1', root / 'e2'
            e1.mkdir()
            jobs = []
            for t in (6, 12):
                ident = f'timing_G_t{t}'
                job = dict(id=ident, graph='G', kind='timing', algo='delta-omp',
                           sources=[0, 1, 2, 3], deltas=[4, 8, 13, 16], reps=3)
                jobs.append(job)
                rows = []
                for delta in job['deltas']:
                    for source in range(4):
                        for rep in range(3):
                            rows.append(dict(variant='all', filter='merge', threads=t, delta=delta,
                                source=source, rep=rep, stats_build=0, verified=1,
                                time_ms=1 if delta == (8 if t == 6 else 13) else 4))
                path = e1 / (ident + '.csv')
                with path.open('w') as f:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                path.with_suffix('.done').write_text(json.dumps({'csv_sha256': digest(path)}))
            manifest = dict(jobs=jobs, profiles={'G': {'sweep': [1, 2, 4, 8, 16]}})
            with patch.object(e2_plan, 'E1', e1), patch.object(e2_plan, 'OUT', out):
                result = prepare('G', manifest)
                self.assertEqual(result['deltas'], [4, 8, 13, 16])
                self.assertEqual(result['anchors'], {'6': 8, '12': 13})
                self.assertEqual(len(result['jobs']), 24)
                self.assertTrue(all(len(j['deltas']) <= 2 for j in result['jobs']))
                self.assertEqual(prepare('G', manifest), result)
                (out / 'G.json').unlink()
                path.write_text('corrupted')
                with self.assertRaises(ValueError):
                    prepare('G', manifest)

    def test_queue_prioritizes_eligible_e2(self):
        job = {'id': 'e2'}
        with patch('e2_driver.ORDER', ['G']), patch('e2_driver.prepare', return_value={'jobs': [job]}), \
                patch('e2_driver.complete', return_value=False):
            self.assertEqual(choose({'jobs': [{'id': 'e1'}]})[0], job)
        with patch('e2_driver.ORDER', []), patch('e2_driver.complete', return_value=True):
            self.assertIsNone(choose({'jobs': [{'id': 'e1'}]}))


if __name__ == '__main__':
    unittest.main()
