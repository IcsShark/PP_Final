#!/usr/bin/env python3
import pathlib
import tempfile
import unittest

from e1_common import digest, read_rows, validate_rows


class ValidationTests(unittest.TestCase):
    def test_verified_rows(self):
        validate_rows([{'verified': '1', 'time_ms': '1.25'}], 1)

    def test_missing_and_empty_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'rows.csv'
            self.assertEqual(read_rows(path), [])
            path.write_text('verified,time_ms\n')
            self.assertEqual(read_rows(path), [])
            with self.assertRaises(RuntimeError):
                validate_rows(read_rows(path), 1)

    def test_failed_and_unverified_rows(self):
        for verified in ('0', '-1', None):
            with self.subTest(verified=verified), self.assertRaises(RuntimeError):
                validate_rows([{'verified': verified, 'time_ms': '1'}], 1)

    def test_bad_times(self):
        for value in ('', '-1', 'nan', 'inf'):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                validate_rows([{'verified': '1', 'time_ms': value}], 1)

    def test_csv_and_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'rows.csv'
            path.write_text('verified,time_ms\n1,2.5\n')
            validate_rows(read_rows(path), 1)
            self.assertEqual(len(digest(path)), 64)


if __name__ == '__main__':
    unittest.main()
