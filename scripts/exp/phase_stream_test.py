#!/usr/bin/env python3
import gzip
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

from e1_common import PHASE_HEADER, ROOT
from e1_worker import run_checked
from phase_stream import PhaseStream

sys.path.insert(0, str(ROOT / 'analysis'))
from e1_phase_reduce import summarize as e1_summarize
from e2_phase_reduce import summarize as e2_summarize

HEADER = ','.join(PHASE_HEADER) + '\n'
ROW = 'NY,delta-seq,all,pop,1,1,42,0,0,0,2,1,8,7\n'


class PhaseStreamTests(unittest.TestCase):
    def write(self, stream, content):
        with stream.path.open('w') as writer:
            writer.write(content)

    def test_header_and_headerless_streams(self):
        for reducer in (e1_summarize, e2_summarize):
            expected = reducer(io.StringIO(HEADER + ROW))
            for content in (HEADER + ROW, ROW):
                with self.subTest(reducer=reducer.__module__, header=content.startswith('graph')):
                    with PhaseStream(reducer) as stream:
                        self.write(stream, content)
                    self.assertEqual(stream.rows, expected)
                    self.assertFalse(stream.path.exists())

    def test_empty_and_malformed_streams(self):
        for content in ('', HEADER, 'broken\n', HEADER + ROW.replace(',0,0,0,2', ',2,0,0,2')):
            with self.subTest(content=content), self.assertRaises(RuntimeError):
                with PhaseStream(e1_summarize) as stream:
                    self.write(stream, content)

    def test_producer_failure_before_fifo_open_does_not_hang(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'kernel exited 3'):
                with PhaseStream(e1_summarize) as stream:
                    run_checked([sys.executable, '-c', 'raise SystemExit(3)'],
                                pathlib.Path(directory) / 'rows.csv', pathlib.Path(directory) / 'log',
                                check=stream.check)

    def test_reducer_failure_terminates_producer(self):
        with tempfile.TemporaryDirectory() as directory:
            code = ('import sys,time; f=open(sys.argv[1], "w"); '
                    'f.write("broken\\n"); f.flush(); time.sleep(60)')
            with self.assertRaisesRegex(RuntimeError, 'phase reducer failed'):
                with PhaseStream(e1_summarize) as stream:
                    run_checked([sys.executable, '-c', code, str(stream.path)],
                                pathlib.Path(directory) / 'rows.csv', pathlib.Path(directory) / 'log',
                                check=stream.check)

    @unittest.skipUnless(os.getenv('NY_PHASE_LOG'), 'set NY_PHASE_LOG to an existing NY raw gzip log on compute')
    def test_existing_ny_raw_log_exact_equivalence(self):
        path = pathlib.Path(os.environ['NY_PHASE_LOG'])
        self.assertTrue(path.is_file())
        code = ('import gzip,shutil,sys; src=gzip.open(sys.argv[1], "rb"); '
                'src.readline(); dst=open(sys.argv[2], "wb"); shutil.copyfileobj(src,dst); dst.close()')
        for reducer in (e1_summarize, e2_summarize):
            with gzip.open(path, 'rt', newline='') as raw:
                old = reducer(raw)
            self.assertTrue(old)
            self.assertEqual({r['graph'] for r in old}, {'NY'})
            start = time.monotonic()
            with PhaseStream(reducer) as stream:
                subprocess.run([sys.executable, '-c', code, str(path), str(stream.path)], check=True, timeout=120)
            self.assertEqual(old, stream.rows)
            print(f'EXACT NY EQUIVALENCE {reducer.__module__}: {len(old)} runs, '
                  f'{sum(r["phases"] for r in old)} phases in {time.monotonic()-start:.3f}s; {path.name}', flush=True)


if __name__ == '__main__':
    unittest.main()
