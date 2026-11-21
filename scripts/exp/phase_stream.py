"""Bounded FIFO transport: phase CSV bytes never enter a regular file."""
import itertools
import os
import pathlib
import tempfile
import threading

from e1_common import PHASE_HEADER


class PhaseStream:
    def __init__(self, reducer):
        self.reducer = reducer
        self.rows = None
        self.errors = []

    def __enter__(self):
        self.directory = tempfile.TemporaryDirectory(prefix='sssp-phase-')
        self.path = pathlib.Path(self.directory.name) / 'phases.fifo'
        os.mkfifo(self.path)
        self.keepalive = os.open(self.path, os.O_RDWR)
        self.reader = self.path.open()
        self.thread = threading.Thread(target=self.consume, daemon=True)
        self.thread.start()
        return self

    def consume(self):
        try:
            with self.reader as stream:
                first = next(stream, '')
                if not first:
                    raise ValueError('empty phase stream')
                prefix = [] if first.rstrip('\r\n').split(',') == PHASE_HEADER else [','.join(PHASE_HEADER) + '\n']
                self.rows = self.reducer(itertools.chain(prefix, [first], stream))
        except BaseException as error:
            self.errors.append(error)

    def check(self):
        if self.errors:
            raise RuntimeError(f'phase reducer failed: {self.errors[0]}') from self.errors[0]

    def __exit__(self, kind, value, traceback):
        os.close(self.keepalive)
        self.thread.join(timeout=30)
        if self.thread.is_alive():
            raise RuntimeError('phase reducer did not finish after producer exit')
        self.directory.cleanup()
        if kind is None:
            self.check()
