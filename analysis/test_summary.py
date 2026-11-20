import unittest

from summary import RULES, render


class SummaryTests(unittest.TestCase):
    def inputs(self):
        q4 = [dict(graph='G', threads=str(t), rule=rule, delta='2', time_ms='3',
            variant='all', filter='pop', status='ok', slowdown='1.25')
            for t in (1, 6, 12) for rule in ('fastest', *RULES)]
        reductions = [dict(graph='G', algo='delta-omp', variant='all', filter='pop',
            comparison='largest_sweep_delta', larger_delta='8', empty_share='0.2')]
        metrics = [dict(graph='G', algo='delta-omp', threads='6', delta='1',
            variant=v, filter=f, phases='10', empty_expanded='2' if f == 'pop' else '0')
            for v in ('all', 'lh') for f in ('pop', 'merge')]
        scaling = [dict(graph='G', threads=str(t), delta='2', time_ms='3',
            speedup_seq='2', speedup_dijkstra='4', efficiency_seq='0.5', ideal_speedup='5',
            ideal_no_max_speedup='6', phases='10', average_parallelism='12')
            for t in (1, 2, 4, 6, 8, 12)]
        return [['G'], q4, reductions, metrics, scaling, '### Hardware fixture\n']

    def test_tables_and_caveats(self):
        text = render(*self.inputs())
        self.assertIn('2 / 3.000 (all/pop)', text)
        self.assertIn('20.00%', text)
        self.assertIn('2 / 1.250×', text)
        self.assertIn('5.000 / 6.000', text)
        self.assertIn('### Hardware fixture', text)
        for phrase in ('t6 counters as a proxy', 'approximately **600 corrupted LJ edges**',
                       'roughly **40×** GAPBS iterations', 'no new cluster runs', 'not proof'):
            self.assertIn(phrase, text)

    def test_empty_partial_and_duplicate_results(self):
        for change in ('empty', 'partial_q4', 'duplicate_rule', 'partial_e2', 'duplicate_e2'):
            args = self.inputs()
            if change == 'empty':
                args[0] = []
            elif change == 'partial_q4':
                args[1].pop()
            elif change == 'duplicate_rule':
                args[1][-1] = args[1][-2]
            elif change == 'partial_e2':
                args[4].pop()
            else:
                args[4][-1] = args[4][-2]
            with self.subTest(change=change), self.assertRaises(ValueError):
                render(*args)

    def test_unavailable_rule(self):
        args = self.inputs()
        args[1][1].update(status='no passing delta', delta='', slowdown='')
        self.assertIn('N/A', render(*args))


if __name__ == '__main__':
    unittest.main()
