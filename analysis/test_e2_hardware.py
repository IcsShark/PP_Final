import unittest

import numpy as np

from e2_hardware import analyze, bandwidth_gbs, fit, leave_delta_out_rmse, markdown


class HardwareTests(unittest.TestCase):
    def rows(self):
        return [dict(graph='G', threads=k, delta=d, ideal_work=(10+d*d)/k,
            phases=2+d, time_ms=0.2*(10+d*d)/k+0.01*k*(2+d), edges_scanned=10+d*d)
            for k in (1, 6, 12) for d in (1, 2, 4, 8)]

    def test_exact_fit_and_held_out_delta(self):
        rows = self.rows()
        result = fit(rows)
        np.testing.assert_allclose(result['coefficients'], [0.2, 0.01, 0.06, 0.12], atol=1e-10)
        self.assertEqual(result['rank'], 4)
        self.assertTrue(result['identifiable'])
        self.assertAlmostEqual(result['r_squared'], 1)
        self.assertLess(result['rmse_ms'], 1e-10)
        self.assertLess(leave_delta_out_rmse(rows), 1e-10)

    def test_nonnegative_boundary_and_rank_warning(self):
        rows = self.rows()
        for r in rows:
            r['time_ms'] = r['ideal_work'] - 0.1*r['phases']
        result = fit(rows)
        self.assertTrue(all(c >= 0 for c in result['coefficients']))
        self.assertTrue(any(c == 0 for c in result['coefficients']))
        self.assertGreater(result['rmse_ms'], 0)
        rows = [dict(r, ideal_work=r['phases']) for r in self.rows()]
        self.assertFalse(fit(rows)['identifiable'])
        self.assertIsNone(leave_delta_out_rmse(rows))

    def test_bandwidth_units_empty_and_errors(self):
        self.assertEqual(bandwidth_gbs(1_000_000, 72), 1)
        self.assertEqual(bandwidth_gbs(0, 1), 0)
        for edges, ms in ((-1, 1), (1, 0), (1, -1), (float('inf'), 1), (1, float('nan'))):
            with self.assertRaises(ValueError):
                bandwidth_gbs(edges, ms)

    def test_empty_and_invalid_observations(self):
        with self.assertRaises(ValueError):
            fit([])
        with self.assertRaises(ValueError):
            analyze([], [])
        self.assertIsNone(leave_delta_out_rmse([]))
        for key, value in (('time_ms', 0), ('time_ms', float('nan')), ('phases', 0), ('ideal_work', -1)):
            with self.assertRaises(ValueError):
                fit([dict(self.rows()[0], **{key: value})])

    def test_split_and_bandwidth_use_winning_delta(self):
        rows = self.rows()
        best = [min((r for r in rows if r['threads'] == k), key=lambda r: r['time_ms']) for k in (1, 6, 12)]
        fits, splits, bandwidth = analyze(rows, best)
        self.assertEqual(len(fits), 1)
        self.assertEqual(len(splits), 3)
        self.assertEqual(len(bandwidth), 2)
        for r, winning in zip(splits, best):
            self.assertEqual(r['delta'], winning['delta'])
            self.assertAlmostEqual(r['work_ms']+r['sync_ms'], r['fitted_ms'])
            self.assertAlmostEqual(r['work_percent']+r['sync_percent'], 100)
            self.assertAlmostEqual(r['measured_ms'], r['fitted_ms'])
        self.assertIn('not a measurement of barrier time', markdown(fits, splits, bandwidth))
        self.assertIn('N/A', markdown([dict(fits[0], leave_delta_out_rmse_ms=None)], splits, bandwidth))

    def test_two_delta_holdout_is_unavailable(self):
        self.assertIsNone(leave_delta_out_rmse([r for r in self.rows() if r['delta'] in (1, 2)]))


if __name__ == '__main__':
    unittest.main()
