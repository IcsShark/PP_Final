import io
import unittest

from e1_phase_reduce import HEADER, summarize


class PhaseReductionTests(unittest.TestCase):
    def stream(self, *rows):
        return io.StringIO(','.join(HEADER) + '\n' + '\n'.join(rows) + '\n')

    def test_counts_empty_definitions_and_heavy_work(self):
        result = summarize(self.stream(
            'G,delta-seq,lh,pop,1,1,0,0,0,0,3,0,0,0',
            'G,delta-seq,lh,pop,1,1,0,1,0,0,0,0,0,0',
            'G,delta-seq,lh,pop,1,1,0,2,0,1,2,2,0,0',
            'G,delta-seq,lh,pop,1,1,0,3,1,0,2,1,7,7'))[0]
        self.assertEqual(result['phases'], 4)
        self.assertEqual(result['empty_frontier'], 1)
        self.assertEqual(result['empty_expanded'], 2)
        self.assertEqual(result['empty_edges'], 3)
        self.assertEqual(result['heavy_phases'], 1)
        self.assertEqual(result['edges_sum'], 7)

    def test_multiple_deltas(self):
        result = summarize(self.stream('G,delta-seq,all,pop,1,1,0,0,0,0,1,1,1,1',
                                       'G,delta-seq,all,pop,1,2,0,0,0,0,1,1,1,1'))
        self.assertEqual([r['delta'] for r in result], ['1', '2'])

    def test_empty_header_and_bad_rows(self):
        for stream in (io.StringIO(''), io.StringIO(','.join(HEADER) + '\n'), self.stream('short')):
            with self.assertRaises(ValueError):
                summarize(stream)

    def test_missing_phase(self):
        with self.assertRaises(ValueError):
            summarize(self.stream('G,delta-seq,all,pop,1,1,0,1,0,0,1,1,1,1'))


if __name__ == '__main__':
    unittest.main()
