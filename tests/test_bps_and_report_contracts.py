"""Portable inherited edge cases; historical renderer tests stay archived."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from bps import BpsError, apply_bps, create_bps
from record_development_verification import parse_unittest_result

class BpsSizeTests(unittest.TestCase):
    def test_growing_target(self):
        self.assertEqual(apply_bps(b"abc", create_bps(b"abc", b"abXYZ123")), b"abXYZ123")

    def test_shrinking_target(self):
        self.assertEqual(apply_bps(b"abcdef", create_bps(b"abcdef", b"ax")), b"ax")

    def test_empty_source_or_target(self):
        for source, target in ((b"", b"x"), (b"abc", b""), (b"", b"")):
            self.assertEqual(apply_bps(source, create_bps(source, target)), target)

    def test_wrong_source_rejected(self):
        with self.assertRaises(BpsError):
            apply_bps(b"abd", create_bps(b"abc", b"abcdef"))


class TestReportTests(unittest.TestCase):
    def test_skipped_word_in_test_name_is_not_a_skipped_result(self):
        self.assertEqual(parse_unittest_result('test_not_silently_skipped ... ok\nRan 73 tests in 3.0s\n\nOK\n',0),73)

    def test_real_skips_cannot_be_promoted_to_pass(self):
        for log in ('test_cpu ... skipped dependency\nRan 73 tests in 3.0s\n\nOK (skipped=1)\n',
                    'Ran 73 tests in 3.0s\n\nOK (skipped=42)\n'):
            with self.assertRaises(ValueError):
                parse_unittest_result(log,0)

    def test_failed_or_missing_result_cannot_be_promoted(self):
        for log,code in (('Ran 1 test in 1.0s\nFAILED (errors=1)\n',1),('OK\n',0)):
            with self.assertRaises(ValueError):
                parse_unittest_result(log,code)
