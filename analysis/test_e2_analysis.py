import io
import unittest

from e2_phase_reduce import HEADER, summarize
from e2_analysis import best_rows, source_medians


class ModelTests(unittest.TestCase):
    def stream(self, *rows):
        return io.StringIO(','.join(HEADER) + '\n' + '\n'.join(rows) + '\n')

    def test_ideal_cost_vertex_bound_and_zero_phase(self):
        r = summarize(self.stream(
            'G,delta-omp,all,pop,6,4,0,0,0,0,2,2,10,8',
            'G,delta-omp,all,pop,6,4,0,1,0,0,2,2,2,1',
            'G,delta-omp,all,pop,6,4,0,2,0,0,0,0,0,0'))[0]
        self.assertEqual(r['phases'], 3)
        self.assertEqual(r['edges'], 12)
        self.assertEqual(r['ideal']['1'], 12)
        self.assertEqual(r['ideal']['6'], 9)
        self.assertEqual(r['ideal_no_max']['6'], 3)

    def test_empty_and_invalid(self):
        for stream in (io.StringIO(''), self.stream(), self.stream('short'),
                       self.stream('G,delta-omp,all,pop,6,4,0,1,0,0,1,1,2,1'),
                       self.stream('G,delta-omp,all,pop,6,4,0,0,0,0,1,1,2,3')):
            with self.assertRaises(ValueError):
                summarize(stream)

    def test_timing_aggregation(self):
        rows = [dict(source=s, time_ms=x+s) for s in range(4) for x in (1, 2, 100)]
        self.assertEqual(source_medians(rows), 3.5)
        for bad in ([], rows[:-1]):
            with self.assertRaises(ValueError):
                source_medians(bad)

    def test_best_delta_and_empty(self):
        self.assertEqual(best_rows([]), [])
        rows = [dict(graph='G', threads=1, delta=d, time_ms=ms) for d, ms in ((2, 5), (4, 3))]
        self.assertEqual(best_rows(rows), [rows[1]])


if __name__ == '__main__':
    unittest.main()
